import json
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from utils import get_alive_heroes, user_link, parse_inline_keyboard_select_user, find_hero_by_user_id
from role import Role


class Investigator(Role):
    """Стандартный класс следователя"""

    def __init__(self, game, user):
        super().__init__(game, user)
        self.investigator_voting_message = None
        self.is_investigator_voted = None
        self.role_name = game.gt("roles.investigator")
        self.role_name_short = game.gt("investigator_role_name_short")
        self.role_description = game.gt("investigator_role_description")

    async def your_move(self, context):
        """Отправляет игроку сообщение о проверке"""
        heroes = get_alive_heroes(self.game.heroes)
        heroes.remove(self)  # Нельзя проверять себя
        self.is_investigator_voted = False
        self.investigator_voting_message = await context.bot.send_message(
            self.user.id,
            text=self.game.gt("investigator_voting"),
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(hero.user.full_name,
                                       callback_data=json.dumps([
                                           'inv voted',
                                           self.game.game_hash,
                                           hero.user.id
                                       ]))]
                 for hero in heroes]))


async def investigator_voted(query, context):
    data_list, game, from_hero, selected_user = parse_inline_keyboard_select_user(query, context)
    await query.answer()
    # Говорим игроку кого он выбрал и пишем роль этого человека
    from_hero.is_investigator_voted = True
    await query.edit_message_text(text=f"{game.gt('investigator_voting')}\n"
                                       f"\n"
                                       f"{game.gt('you_chosen')} {user_link(selected_user)}"
                                       f"\n"
                                       f"{game.gt('this_guy_role_is')}"
                                       f"{game.gt(find_hero_by_user_id(selected_user.id, game).role_name_short)}",
                                  parse_mode=ParseMode.HTML)
    # Добавляем информацию о выборе игрока в действующую ночь
    game.working_night['investigator_voting'] = {
        'selected_user_id': selected_user.id
    }
