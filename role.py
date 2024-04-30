import json
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from utils import get_alive_heroes, user_link, parse_inline_keyboard_select_user, chat_gt, find_hero_by_user_id


class Role:
    """Базовый класс роли"""

    def __init__(self, game, user):
        """
            Initialization of role class.
            ARGUMENTS:
                - game object for role
                    <Game> game
                - user playing for the role
                    <User> user
            RETURNS:
                None
        """
        self.game = game
        self.user = user
        self.is_alive = True
        self.role_name = game.gt("roles.citizen")
        self.role_name_short = game.gt("citizen_role_name_short")
        self.role_description = game.gt("citizen_role_description")
        self.team = 'citizens'

    async def say_hi(self, context):
        """Объявляет игроку его роль"""
        await context.bot.send_message(
            self.user.id,
            text=f'<b>{self.game.gt("you_capital")} - {self.game.gt(self.role_name)}!</b>\n'
                 f'{self.game.gt(self.role_description)}',
            parse_mode=ParseMode.HTML)

    async def say_goodbye(self, context):
        """Сообщает игроку о смерти"""
        await context.bot.send_message(
            self.user.id,
            text=f'<b>{self.game.gt("you_were_killed")}</b>',
            parse_mode=ParseMode.HTML)

    async def day_vote(self, context):
        """Отправляет игроку сообщение о дневном голосовании"""
        if self.is_alive:
            heroes = get_alive_heroes(self.game.heroes)
            heroes.remove(self)

            await context.bot.send_message(
                self.user.id,
                text=f'<b>{self.game.gt("time_for_finding_bad_people")}!</b>\n'
                     f'{self.game.gt("who_do_yoy_want_to_kill")}\n',
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(hero.user.full_name,
                                           callback_data=json.dumps([
                                               'day voted',
                                               self.game.game_hash,
                                               hero.user.id
                                           ]))]
                     for hero in heroes]),
                parse_mode=ParseMode.HTML)

    async def your_move(self, context):
        pass


async def day_voted(query, context):
    data_list, game, from_hero, selected_user = parse_inline_keyboard_select_user(query, context)
    await query.answer()

    # Говорим игроку кого он выбрал
    await query.edit_message_text(text=f'<b>{game.gt("time_for_finding_bad_people")}</b>\n'
                                       f'{game.gt("who_do_yoy_want_to_kill")}\n'
                                       f'\n'
                                       f'{game.gt("you_chosen")} {user_link(selected_user)}',
                                  parse_mode=ParseMode.HTML)

    # Добавляем информацию о выборе игрока в действующий день
    game.working_day['users_voting'].append({
        'user_id': from_hero.user.id,
        'selected_user_id': selected_user.id
    })

    # Проверяем не проголосовали ли все игроки
    if not game.working_day['voting_ended'] and len(game.users) == len(game.working_day['users_voting']):
        await game.day_voting_ended(context)


async def day_check_voted(query, context):
    data_list = json.loads(query.data)
    from_user = query.from_user
    game = context.bot_data[data_list[1]]

    if from_user in game.users:
        if find_hero_by_user_id(from_user.id, game).is_alive:
            if from_user.id != game.working_day['suggested_user_id']:
                if from_user.id in game.working_day['result_check']:
                    if bool(data_list[2]) == game.working_day['result_check'][from_user.id]:
                        return
                game.working_day['result_check'][from_user.id] = bool(data_list[2])

                await context.bot.edit_message_reply_markup(
                    chat_id=game.chat_id,
                    message_id=game.working_day['day_vote_check_message'].id,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(text=game.gt('voting_check_+',
                                                           cnt=len(list(filter(lambda answer: answer is True,
                                                                               game.working_day[
                                                                                   'result_check'].values())))),
                                              callback_data=json.dumps([
                                                  'day check voted',
                                                  game.game_hash,
                                                  1
                                              ]))],
                        [InlineKeyboardButton(text=game.gt('voting_check_-',
                                                           cnt=len(list(filter(lambda answer: answer is False,
                                                                               game.working_day[
                                                                                   'result_check'].values())))),
                                              callback_data=json.dumps([
                                                  'day check voted',
                                                  game.game_hash,
                                                  0
                                              ]))]
                    ])
                )
            else:
                await query.answer(chat_gt('its_not_for_you', context))
        else:
            await query.answer(chat_gt('its_not_for_died', context))
    else:
        await query.answer(chat_gt('you_are_not_in_game', context))
