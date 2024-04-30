import json
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from utils import get_alive_heroes, user_link, parse_inline_keyboard_select_user, find_hero_by_user_id
from role import Role


class Doctor(Role):
    """Стандартный класс доктора"""

    def __init__(self, game, user):
        super().__init__(game, user)
        self.doctor_voting_message = None
        self.is_doctor_voted = None
        self.role_name = game.gt("roles.doctor")
        self.role_name_short = game.gt("doctor_role_name_short")
        self.role_description = game.gt("doctor_role_description")
        self.last = None

    async def your_move(self, context):
        """Отправляет игроку сообщение о лечении"""
        heroes = get_alive_heroes(self.game.heroes)
        if self.last:  # Убираем того, кого полечили в последний раз
            heroes.remove(find_hero_by_user_id(self.last, self.game))
        print(heroes)
        self.is_doctor_voted = False
        self.doctor_voting_message = await context.bot.send_message(
            self.user.id,
            text=self.game.gt("doctor_voting"),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(hero.user.full_name,
                                       callback_data=json.dumps([
                                           'doc voted',
                                           self.game.game_hash,
                                           hero.user.id
                                       ]))]
                 for hero in heroes]))


async def doctor_voted(query, context):
    data_list, game, from_hero, selected_user = parse_inline_keyboard_select_user(query, context)
    await query.answer()
    # Говорим игроку кого он выбрал
    from_hero.is_doctor_voted = True
    await query.edit_message_text(text=f"{game.gt('doctor_voting')}\n"
                                       f"\n"
                                       f"{game.gt('you_chosen')} {user_link(selected_user)}",
                                  parse_mode=ParseMode.HTML)

    # Добавляем информацию о выборе игрока в действующую ночь
    game.working_night['doctor_voting'] = {
        'selected_user_id': selected_user.id
    }
    from_hero.last = selected_user.id  # Записываем того, кого вылечили
