"""Импортируем всё, что нам нужно"""
import json

import telegram

from data import db_session
from telegram.ext import Application, CommandHandler, filters, MessageHandler, CallbackQueryHandler
from telegram.constants import ParseMode

from utils import parse_command, chat_id_to_game_hash, chat_gt, user_link, get_chat_settings, parse_rating
from config import BOT_TOKEN, DEFAULT_SETTINGS
from game import Game
from mafia import mafia_voted
from doctor import doctor_voted
from investigator import investigator_voted
from role import day_voted, day_check_voted
from chat_settings import chat_settings_clicked, chat_settings_update, edit_chat_settings
from db_plugin import get_user_rating, get_users_in_chat_rating, add_chat

ALL_ROLES = ['mafia', 'doctor', 'don', 'citizen', 'investigator', 'mistress', 'sheriff']  # Все роли
THIS_GAME_ROLES = []  # Роли в этой игре


async def commands(update, context):
    """Функция возвращает список всех команд после команды /help"""
    await context.bot.send_message(
        update.effective_chat.id,
        f'{chat_gt("all_commands", context)}\n'
        f'{chat_gt("command_game", context)},\n'
        f'{chat_gt("command_start", context)},\n'
        f'{chat_gt("command_stop", context)},\n'
        f'{chat_gt("command_extend", context)},\n'
        f'{chat_gt("command_role", context)}, \n'
        f'{chat_gt("command_roles", context)},\n'
        f'{chat_gt("command_settings", context)}.'
    )


async def text_messages_handler(update, context):
    """Обрабатывает все текстовые сообщения отправленные боту"""
    if update.effective_chat.type in ['supergroup', 'group']:  # Если сообщения отправлено из группы
        if chat_id_to_game_hash(update.effective_chat.id) in context.bot_data.keys():  # Если в ней идёт игра
            if context.bot_data[chat_id_to_game_hash(update.effective_chat.id)].started:  # Если игра уже началась
                if update.effective_user not in context.bot_data[chat_id_to_game_hash(update.effective_chat.id)].users:
                    # Если отправитель не играет сейчас в этом чате
                    await update.message.delete()
    elif update.effective_chat.type == 'private':  # Если в личном чате
        if 'last_game_hash' in context.user_data.keys():
            if context.user_data['last_game_hash'] in context.bot_data.keys():  # Если он играет в игру
                user_playing_game = context.bot_data[context.user_data['last_game_hash']]
                user_role = list(filter(lambda x: x.user.id == update.effective_user.id, user_playing_game.heroes))[0]
                if user_role.is_alive:  # Если он жив
                    if type(user_role).__name__ in ['Don', 'Mafia']:  # Если он из мафии
                        # Отправляем сообщение в чат мафии
                        await user_playing_game.mafia_mail_sent(update.effective_user, update.message.text, context)
                else:
                    # Отправляем предсмертное письмо
                    await user_playing_game.user_sent_last_message(user_role, update.message.text, context)


async def game_check_in_start(update, context):
    """Функция начинает регистрацию на новую игру"""
    if update.effective_chat.type in ['supergroup', 'group']:
        game_hash = chat_id_to_game_hash(update.effective_chat.id)
        if 'settings' not in context.chat_data.keys():
            context.chat_data['settings'] = DEFAULT_SETTINGS
        context.bot_data[game_hash] = Game(game_hash, update.effective_chat, get_chat_settings(context))
        await context.bot_data[game_hash].start_check_in(context)
    elif update.effective_chat.type == 'private':  # Если пользователь делает это в лс, то пишем ошибку
        await context.bot.send_message(
            update.effective_chat.id,
            f'<b>{chat_gt("chat_error", context)}</b>',
            parse_mode=ParseMode.HTML
        )


async def game_check_in_stop(update, context):
    """Функция останавливает регистрацию"""
    if update.effective_chat.type in ['supergroup', 'group']:
        if chat_id_to_game_hash(update.effective_chat.id) in context.bot_data.keys():
            if not context.bot_data[chat_id_to_game_hash(update.effective_chat.id)].is_started:
                await context.bot_data[chat_id_to_game_hash(update.effective_chat.id)].stop_check_in(context)
    elif update.effective_chat.type == 'private':  # Если пользователь делает это в лс, то пишем ошибку
        await context.bot.send_message(
            update.effective_chat.id,
            f'<b>{chat_gt("chat_error", context)}</b>',
            parse_mode=ParseMode.HTML
        )


async def start(update, context):
    """Функция имеет много развилов"""
    if update.effective_chat.type in ['supergroup', 'group']:  # Если групповой чат, то начать игру, окончив регистарцию
        await context.bot_data[chat_id_to_game_hash(update.effective_chat.id)].start_stop_game(context)
    elif update.effective_chat.type == 'private':  # Если личный чат И сообщение с хэшом, то это регистарция
        game_hash = parse_command(update.message.text, 'start')  # Отделяем хэш от команды
        if game_hash:
            context.user_data['last_game_hash'] = game_hash
            await context.bot_data[game_hash].add_user(update, context)
        else:  # Если личный чат И сообщение без хэша, то это знакомство
            await context.bot.send_message(
                update.effective_chat.id,
                f'<b>{chat_gt("hello", context)}, {user_link(update.effective_user)}!</b>\n'
                f'{chat_gt("information", context)}\n'
                f'{chat_gt("help", context)}',
                parse_mode=ParseMode.HTML
            )


async def users_rating(update, context):
    if update.effective_chat.type in ['supergroup', 'group']:
        rating = get_users_in_chat_rating(update.effective_chat)
        await update.message.delete()
        if rating:
            await context.bot.send_message(
                update.effective_chat.id,
                text=f"{chat_gt('rating_in_group', context, group_title=update.effective_chat.title)}\n"
                     f"\n"
                    f"{parse_rating(rating)}\n",
                parse_mode=ParseMode.HTML)
        else:
            await context.bot.send_message(
                update.effective_chat.id,
                text=f"{chat_gt('in_group_not_played_any_game', context, group_title=update.effective_chat.title)}\n")
    elif update.effective_chat.type == 'private':
        rating = get_user_rating(update.effective_user)
        await update.message.delete()
        if rating['played_games']:
            await context.bot.send_message(
                update.effective_chat.id,
                text = chat_gt('your_rating',
                               context,
                               played_games=rating['played_games'],
                               wins=rating['wins']))
        else:
            await context.bot.send_message(
                update.effective_chat.id,
                text = f"{chat_gt('you_didnt_play_any_game', context)}\n")
        print(rating)


async def extend_game_check_in(update, context):
    """Функция, которая продлевает регистрацию"""
    if update.effective_chat.type  in ['supergroup', 'group']:
        await context.bot_data[chat_id_to_game_hash(update.effective_chat.id)].extend_check_in(context)
    elif update.effective_chat.type == 'private':  # Если пользователь делает это в лс, то пишем ошибку
        await context.bot.send_message(
            update.effective_chat.id,
            f'<b>{chat_gt("chat_error", context)}</b>',
            parse_mode=ParseMode.HTML
        )


async def inline_keyboard_handler(update, context):
    """Функция, которая обрабатывает запросы inline-клавиатур"""
    query = update.callback_query
    data_list = json.loads(query.data)
    handlers = {
        'maf voted': mafia_voted,
        'doc voted': doctor_voted,
        'inv voted': investigator_voted,
        'day voted': day_voted,
        'day check voted': day_check_voted,
        'chat settings clicked': chat_settings_clicked,
        'chat settings update': chat_settings_update
    }
    await handlers[data_list[0]](query, context)


async def all_roles(update, context):
    """Функция, которая выводит все роли"""
    await context.bot.send_message(
        update.effective_chat.id,
        f'{chat_gt("all_roles", context)}',
        parse_mode=ParseMode.HTML
    )


async def about_role(update, context):
    """Функция описания отдельной роли"""
    role = parse_command(update.message.text, 'role').lower()
    if role in ALL_ROLES:  # Проверяем, что у нас такая есть
        await context.bot.send_message(
            update.effective_chat.id,
            f'{chat_gt(role + "_info", context)}',
            parse_mode=ParseMode.HTML
        )
    else:  # Если нет, то ошибка
        await context.bot.send_message(
            update.effective_chat.id,
            f'{chat_gt("no_role_error", context)}',
            parse_mode=ParseMode.HTML
        )


async def new_member(update, context):
    for member in update.message.new_chat_members:
        if member.username == context.bot.username:
            add_chat(update.effective_chat)

async def group_settings(update, context):
    """Функция меню настроек"""
    if 'settings' not in context.chat_data.keys():
        context.chat_data['settings'] = DEFAULT_SETTINGS
    await edit_chat_settings(update, context)

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("help", commands))
    application.add_handler(CommandHandler("game", game_check_in_start))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("extend", extend_game_check_in))
    application.add_handler(CommandHandler("stop", game_check_in_stop))
    application.add_handler(CommandHandler("role", about_role))
    application.add_handler(CommandHandler("roles", all_roles))
    application.add_handler(CommandHandler("settings", group_settings))
    application.add_handler(CommandHandler("rating", users_rating))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    text_handler = MessageHandler(filters.TEXT, text_messages_handler)
    application.add_handler(CallbackQueryHandler(inline_keyboard_handler))
    application.add_handler(text_handler)
    application.run_polling(allowed_updates=telegram.Update.ALL_TYPES)


if __name__ == '__main__':
    db_session.global_init("./db/mafia_users.db")
    main()
