import json
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from utils import get_alive_heroes, user_link, parse_inline_keyboard_select_user
from role import Role


class Mafia(Role):
    """Стандартный класс члена мафии"""

    def __init__(self, game, user):
        super().__init__(game, user)
        self.mafia_voting_message = None
        self.is_mafia_voted = None
        self.role_name = game.gt("roles.mafia")
        self.role_name_short = game.gt("mafia_role_name_short")
        self.role_description = game.gt("mafia_role_description")
        self.team = 'mafia'

    async def your_move(self, context):
        """Отправляет игроку сообщение о голосовании мафии"""
        heroes = get_alive_heroes(self.game.heroes)
        heroes.remove(self)
        self.is_mafia_voted = False
        self.mafia_voting_message = await context.bot.send_message(
            self.user.id,
            text=self.game.gt("mafia_voting"),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(hero.user.full_name,
                                       callback_data=json.dumps([
                                           'maf voted',
                                           self.game.game_hash,
                                           hero.user.id
                                       ]))]
                 for hero in heroes]))


async def mafia_friend_voted(who_to_send, mafia, selected_user, game, context):
    await context.bot.send_message(who_to_send.user.id,
                                   text=f'{mafia.role_name_short} {user_link(mafia.user)} '
                                        f'{game.gt("voted_for")} {user_link(selected_user)}',
                                   parse_mode=ParseMode.HTML)


async def mafia_voted(query, context):
    data_list, game, from_hero, selected_user = parse_inline_keyboard_select_user(query, context)
    await query.answer()
    # Говорим игроку кого он выбрал
    from_hero.is_mafia_voted = True
    await query.edit_message_text(text=f"{game.gt('mafia_voting')}\n"
                                       f"\n"
                                       f"{game.gt('you_chosen')} {user_link(selected_user)}",
                                  parse_mode=ParseMode.HTML)

    # Объявляем остальным членам мафии о выборе игрока
    for mafia in game.mafia_list:
        if mafia != from_hero:
            await mafia_friend_voted(mafia, from_hero, selected_user, game, context)

    # Добавляем информацию о выборе игрока в действующую ночь
    game.working_night['mafia_voting']['voting_results'].append({
        'user_id': from_hero.user.id,
        'user_role': type(from_hero).__name__,
        'selected_user_id': selected_user.id
    })

    # Если игрок Дон, то записываем итог голосования
    if type(from_hero).__name__ == 'Don':
        game.working_night['mafia_voting']['result_user_id'] = selected_user.id

    # Проверяем не проголосовали ли все члены мафии
    if len(game.mafia_list) == len(game.working_night['mafia_voting']['voting_results']):
        await game.mafia_voting_ended(context)
