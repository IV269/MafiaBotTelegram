import random
import json
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from datetime import datetime, timedelta

from config import BOT_LINK, CITIES
from utils import gt, user_link, get_alive_heroes, get_heroes_counts, parse_seconds, \
    alive_users_str_list, plural_seconds_ru, find_user_by_id, find_hero_by_user_id, find_hero_by_role, calculate_roles, \
    if_game_end, remove_job_if_exists, game_ended_message, get_alive_heroes_in_team
from db_plugin import raise_user_rating, add_user, add_user_to_chat, add_chat
from weather_api import forecast
from don import Don
from doctor import Doctor
from mafia import Mafia
from lucky import Lucky
from role import Role
from investigator import Investigator


class Game:
    """Класс игры"""

    def __init__(self, game_hash, chat, settings):
        self.working_day = None
        self.day_num = 0
        self.check_in_end_datetime = None
        self.game_enter_message = None
        self.game_hash = game_hash
        self.settings = settings
        self.users = []
        self.heroes = []
        self.mafia_list = []
        self.check_in_messages = []
        self.chat_id = chat.id
        self.chat = chat
        self.started = False
        self.ended = False
        self.working_night = {}
        self.all_sent_messages = []
        self.game_enter_inline_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(text=self.gt('enter_game'),
                                  url=f'{BOT_LINK}?start={self.game_hash}')]
        ])
        self.go_to_bot_keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(text=self.gt('go_to_bot'),
                                 url=BOT_LINK)
        ]])
        self.go_to_vote_keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(text=self.gt('vote'),
                                 url=BOT_LINK)
        ]])
        self.voting_check_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(text=self.gt('voting_check_+', cnt=0),
                                  callback_data=json.dumps([
                                      'day check voted',
                                      self.game_hash,
                                      1
                                  ]))],
            [InlineKeyboardButton(text=self.gt('voting_check_-', cnt=0),
                                  callback_data=json.dumps([
                                      'day check voted',
                                      self.game_hash,
                                      0
                                  ]))]
        ])
        self.roles_voting_end_handlers = {
            'Doctor': self.doctor_voting_ended,
            'Investigator': self.investigator_voting_ended
        }

    def gt(self, key, **placeholders):
        return gt(key, self.settings, **placeholders)

    def __repr__(self):
        return f'<Game> {self.game_hash}'

    async def start_check_in(self, context):
        """Отправляет сообщение для регистрации, запускает таймеры регистрации"""
        self.game_enter_message = await context.bot.send_message(
            self.chat_id,
            f'<b>{self.gt("game_check_in_started")}</b>',
            parse_mode=ParseMode.HTML,
            reply_markup=self.game_enter_inline_keyboard
        )
        self.check_in_end_datetime = datetime.utcnow() + timedelta(seconds=self.settings['timings']['checkin'])

        self.set_check_in_events(context)

    async def extend_check_in(self, context):
        """Продлевает регистрацию"""
        self.check_in_end_datetime += timedelta(seconds=30)
        check_in_time_left = self.check_in_end_datetime - datetime.utcnow()

        self.check_in_messages.append(await context.bot.send_message(
            self.chat_id,
            f'{self.gt("extend_check_in")}\n'
            f'{self.gt("time_to_check_in_left")} '
            f'{parse_seconds(check_in_time_left.seconds, self)}',
            ParseMode.HTML, reply_markup=self.game_enter_inline_keyboard
        ))

        self.set_check_in_events(context)

    def set_check_in_events(self, context):
        """Устанавливает таймеры регистрации"""
        remove_job_if_exists(f"{self} first check in warning", context)
        remove_job_if_exists(f"{self} second check in warning", context)

        warning_datetime = self.check_in_end_datetime - timedelta(seconds=60)
        if warning_datetime > datetime.utcnow():
            context.job_queue.run_once(self.check_in_warning, warning_datetime,
                                       chat_id=self.chat_id,
                                       name=f"{self} first check in warning")

        warning_datetime = self.check_in_end_datetime - timedelta(seconds=30)
        if warning_datetime > datetime.utcnow():
            context.job_queue.run_once(self.check_in_warning, warning_datetime,
                                       chat_id=self.chat_id,
                                       name=f"{self} second check in warning")

        context.job_queue.run_once(self.start_stop_game, self.check_in_end_datetime,
                                   chat_id=self.chat_id,
                                   name=f'{self} start/stop')

    async def check_in_warning(self, context):
        """Предупреждение о скором окончании регистрации"""
        self.check_in_messages.append(await context.bot.send_message(
            self.chat_id,
            text=f'{self.gt("time_to_check_in_left_var_2")} '
                 f'{(self.check_in_end_datetime - datetime.utcnow()).seconds} сек',
            reply_markup=self.game_enter_inline_keyboard,
            reply_to_message_id=self.game_enter_message.id))

    async def delete_check_in_messages(self):
        """Удаляет все сообщения относящиеся к регистрации"""
        await self.game_enter_message.delete()
        for message in self.check_in_messages:
            await message.delete()

    async def start_stop_game(self, context):
        """Останавливает регистрацию и либо начинает игру, либо нет"""
        await self.delete_check_in_messages()

        if len(self.users) >= 1:
            self.started = True
            self.all_sent_messages.append(await context.bot.send_message(
                self.chat_id,
                text=f'<b>{self.gt("starting_game")}</b>',
                parse_mode=ParseMode.HTML))
            await self.give_roles(context)
            city = random.choice(CITIES)
            
            await context.bot.send_message(
                self.chat_id,
                text=f'<b>{city["title"]}</b>\n'
                     f'{city["description"]}\n',
                parse_mode=ParseMode.HTML)
            await self.start_night(context)
        else:
            await self.stop_check_in(context)
            self.all_sent_messages.append(await context.bot.send_message(
                self.chat_id,
                text=f'<b>{self.gt("not_enough_people_to_start")}</b>\n'
                     f'\n'
                     f'{self.gt("min_people_to_start")}',
                parse_mode=ParseMode.HTML))

    async def add_user(self, update, context):
        """Добавляет игрока в игру, проверяя не находится ли он уже в ней.
        В противном случае пишет ему об этом"""
        if update.effective_user not in self.users:
            self.users.append(update.effective_user)
            in_game_users = [user_link(user) for user in self.users]

            await self.game_enter_message.edit_text(
                f"<b>{self.gt('game_check_in_started')}</b>\n"
                f"\n"
                f"{self.gt('already_checked_in')}\n"
                f"{', '.join(in_game_users)}\n"
                f"\n{self.gt('total')} <b>{len(in_game_users)}</b> {self.gt('people_short')}",
                parse_mode=ParseMode.HTML,
                reply_markup=self.game_enter_inline_keyboard)

            await context.bot.send_message(
                update.effective_message.chat_id,
                text=f'{self.gt("you_joined_game_in")} <b>{self.chat.title}</b>!',
                reply_to_message_id=update.effective_message.id,
                parse_mode=ParseMode.HTML)
        else:
            await context.bot.send_message(update.effective_user.id, text=self.gt('hey_you_already_in_game'))

    async def stop_check_in(self, context):
        """Останавливает регистрацию"""
        self.all_sent_messages.append(await context.bot.send_message(
            self.chat_id, text=self.gt('registration_cancelled')))

    async def give_roles(self, context):
        """Раздаёт игрокам роли и знакомит с ними. Также знакомит мафию"""
        roles = calculate_roles(len(self.users), self.settings)
        random.shuffle(roles)
        for i in range(len(self.users)):
            if roles[i] == 'don':
                hero = Don(self, self.users[i])
                self.mafia_list.append(hero)
            elif roles[i] == 'mafia':
                hero = Mafia(self, self.users[i])
                self.mafia_list.append(hero)
            elif roles[i] == 'doctor':
                hero = Doctor(self, self.users[i])
            elif roles[i] == 'citizen':
                hero = Role(self, self.users[i])
            elif roles[i] == 'lucky':
                hero = Lucky(self, self.users[i])
            elif roles[i] == 'investigator':
                hero = Investigator(self, self.users[i])
            self.heroes.append(hero)
            await self.heroes[i].say_hi(context)
        # hero = Doctor(self, self.users[0])
        # self.heroes.append(hero)
        # await self.heroes[0].say_hi(context)
        # hero = Lucky(self, self.users[0])
        # self.heroes.append(hero)
        # await self.heroes[0].say_hi(context)

    async def send_night_start_message(self, context):
        """Отправляет сообщение о начале ночи"""
        await context.bot.send_message(
            self.chat_id,
            text=f'<b>{self.gt("night_is_starting")}:</b>\n'
                 f'{self.gt("starting_night_description")}',
            parse_mode=ParseMode.HTML,
            reply_markup=self.go_to_bot_keyboard)

    async def send_day_start_message(self, context):
        """Отправляет сообщение о начале дн"""
        await context.bot.send_message(
            self.chat_id,
            text=f'<b>{self.gt("day")} {self.day_num}</b>\n'
                 f'{self.gt("starting_day_description")}',
            parse_mode=ParseMode.HTML)

    async def start_night(self, context):
        """Запускает ночь"""
        self.working_night = {
            'mafia_voting': {
                'voting_results': [],
                'result_user_id': None,
                'is_result_told': None
            },
            'doctor_voting': {
                'selected_user_id': None
            }
        }
        await self.send_night_start_message(context)
        await self.send_alive_users_night_var(context)
        for hero in self.heroes:
            if hero.is_alive:
                await hero.your_move(context)

        context.job_queue.run_once(self.night_ended, self.settings['timings']['night'],
                                   chat_id=self.chat_id,
                                   name=f'{self} night ended')

    async def mafia_voting_ended(self, context):
        """Объявляет всей мафии результат голосования(так как может быть отправлена
         не в самый конец ночи, проверяется не повторяется ли её вызов за счёт
         флага is_result_told)"""
        if not self.working_night['mafia_voting']['is_result_told']:
            for mafia in self.mafia_list:
                if not mafia.is_mafia_voted:
                    await mafia.mafia_voting_message.edit_text(f"{self.gt('mafia_voting')}\n"
                                                               f"\n"
                                                               f"{self.gt('you_late')}",
                                                               parse_mode=ParseMode.HTML)

            self.working_night['mafia_voting']['is_result_told'] = True
            if self.working_night["mafia_voting"]["result_user_id"]:
                killed_user = find_user_by_id(self.working_night["mafia_voting"]["result_user_id"], self)

                for hero in self.mafia_list:
                    await context.bot.send_message(
                        hero.user.id,
                        text=f'{self.gt("mafia_voting_ended")}\n'
                             f'\n'
                             f'{self.gt("mafia_killed")} '
                             f'{user_link(killed_user)}',
                        parse_mode=ParseMode.HTML)

    async def doctor_voting_ended(self, context):
        """Объявляет всей мафии результат голосования(так как может быть отправлена
                 не в самый конец ночи, проверяется не повторяется ли её вызов за счёт
                 флага is_result_told)"""
        doctor = find_hero_by_role('doctor', self)
        if not doctor.is_doctor_voted:
            await doctor.doctor_voting_message.edit_text(f"{self.gt('doctor_voting')}\n"
                                                         f"\n"
                                                         f"{self.gt('you_late')}",
                                                         parse_mode=ParseMode.HTML)
        if self.working_night["doctor_voting"]["selected_user_id"]:
            healed_user = find_hero_by_user_id(self.working_night["doctor_voting"]["selected_user_id"], self)
            print(healed_user)

    async def investigator_voting_ended(self, context):
        investigator = find_hero_by_role('investigator', self)
        if not investigator.is_investigator_voted:
            await investigator.investigator_voting_message.edit_text(f"{self.gt('investogator_voting')}\n"
                                                                     f"\n"
                                                                     f"{self.gt('you_late')}",
                                                                     parse_mode=ParseMode.HTML)

    async def night_ended(self, context):
        """Запускает все процессы по истечении ночи"""
        await self.mafia_voting_ended(context)
        for hero in self.heroes:
            if type(hero).__name__ in self.roles_voting_end_handlers:
                await self.roles_voting_end_handlers[type(hero).__name__](context)
        await self.check_alives(context)
        await self.start_day(context)

    async def night_is(self, context, with_deaths):
        """Пишет есть ли жертвы"""
        if with_deaths:
            await context.bot.send_message(
                self.chat_id,
                text=f'<b>{self.gt("someone_die")} '
                     f'{user_link(find_user_by_id(self.working_night["mafia_voting"]["result_user_id"], self))}</b>',
                parse_mode=ParseMode.HTML)
        else:
            await context.bot.send_message(
                self.chat_id,
                text=f'<b>{self.gt("noone_die")}</b>',
                parse_mode=ParseMode.HTML)

    async def check_alives(self, context):
        """Функция определяет жертв"""
        doc = find_hero_by_role('Doctor', self)
        healed_hero = None
        if doc is not None:
            if doc.is_alive:
                if self.working_night["doctor_voting"]["selected_user_id"] is not None:
                    healed_hero = find_hero_by_user_id(self.working_night["doctor_voting"]["selected_user_id"], self)
        killed_hero = None
        if self.working_night["mafia_voting"]["result_user_id"] is not None:
            killed_hero = find_hero_by_user_id(self.working_night["mafia_voting"]["result_user_id"], self)
        if healed_hero != killed_hero and type(killed_hero) != Lucky:
            killed_hero.is_alive = False
            await killed_hero.say_goodbye(context)
            await self.night_is(context, True)
        else:
            await self.night_is(context, False)

    async def check_game_end(self, context):
        status = if_game_end(self)
        if status is not None:
            for job in context.job_queue.jobs():
                if self.game_hash in job.name:
                    remove_job_if_exists(job.name, context)
            await context.bot.send_message(
                self.chat_id,
                text=game_ended_message(status, self),
                parse_mode=ParseMode.HTML)
            won_heroes = get_alive_heroes_in_team(status, self)
            add_chat(self.chat)
            for hero in self.heroes:
                add_user(hero.user)
                add_user_to_chat(hero.user, self.chat)
                raise_user_rating(hero.user, self.chat, int(hero in won_heroes))
            return True

    async def start_day(self, context):
        """Запускает день"""
        if await self.check_game_end(context):
            self.started = False
            return
        print('start_day')
        self.day_num += 1
        self.working_day = {
            'users_voting': [],
            'result_user_id': None,
            'suggested_user_id': None,
            'result_check': {},
            'day_vote_check_message': None,
            'voting_ended': False
        }
        await self.send_day_start_message(context)
        await self.send_alive_users_day_var(context)

        context.job_queue.run_once(self.start_day_voting, self.settings['timings']['day'],
                                   chat_id=self.chat_id,
                                   name=f'{self} day talk ended')

    async def start_day_voting(self, context):
        """Начинает дневное голосование"""
        await context.bot.send_message(
            self.chat_id,
            text=f'<b>{self.gt("time_to_find_and_kill_bad_people")}</b>\n'
                 f'{self.gt("vote_will_run")} {self.settings["timings"]["day_voting"]} '
                 f'{plural_seconds_ru(self.settings["timings"]["day_voting"])}',
            parse_mode=ParseMode.HTML,
            reply_markup=self.go_to_vote_keyboard)

        for hero in self.heroes:
            await hero.day_vote(context)

        context.job_queue.run_once(self.day_voting_ended, self.settings['timings']['day_voting'],
                                   chat_id=self.chat_id,
                                   name=f'{self} day voting ended')

    async def day_voting_ended(self, context):
        voting_results = {}
        print('day_voting_ended')
        if not self.working_day['voting_ended']:
            self.working_day['voting_ended'] = True
            for vote in self.working_day['users_voting']:
                voting_results[vote['selected_user_id']] = voting_results.get(vote['selected_user_id'], 0) + 1

            if voting_results != {}:
                max_votes = max(voting_results.values())
                users_with_max_votes = list(filter(lambda x: voting_results[x] == max_votes, voting_results.keys()))
                if len(users_with_max_votes) == 1:
                    self.working_day['suggested_user_id'] = users_with_max_votes[0]
                    await self.start_day_voting_result_check(context)
                else:
                    await context.bot.send_message(
                        self.chat_id,
                        text=f'{self.gt("opinions_diff_and_people_go_away")}')
                    await self.start_night(context)
            else:
                await context.bot.send_message(
                    self.chat_id,
                    text=f'{self.gt("opinions_diff_and_people_go_away")}')
                await self.start_night(context)

    async def start_day_voting_result_check(self, context):
        print(self.working_day)
        self.working_day['day_vote_check_message'] = await context.bot.send_message(
            self.chat_id,
            text=f'{self.gt("do_you_want_to_kill")} '
                 f'{user_link(find_user_by_id(self.working_day["suggested_user_id"], self))}?',
            parse_mode=ParseMode.HTML,
            reply_markup=self.voting_check_keyboard)

        context.job_queue.run_once(self.day_voting_result_check_ended, self.settings['timings']['day_vote_check'],
                                   chat_id=self.chat_id,
                                   name=f'{self} day vote check ended')

    async def day_voting_result_check_ended(self, context):
        pluses = len(list(filter(lambda x: x is True, self.working_day['result_check'].values())))
        print(self.working_day, pluses)
        if pluses * 2 > len(self.working_day['result_check'].values()):
            self.working_day['result_user_id'] = self.working_day['suggested_user_id']
            await self.day_kill(context)
        else:
            await self.working_day['day_vote_check_message'].edit_text(
                text=f'{self.gt("do_you_want_to_kill")} '
                     f'{user_link(find_user_by_id(self.working_day["suggested_user_id"], self))}?\n'
                     f'\n'
                     f'{self.gt("opinions_diff_and_people_go_away")}',
                parse_mode=ParseMode.HTML,
                reply_markup=None)
            await self.start_night(context)

    async def day_kill(self, context):
        print(self.working_day["result_user_id"])
        await self.working_day['day_vote_check_message'].edit_text(
            text=f'{self.gt("do_you_want_to_kill")} '
                 f'{user_link(find_user_by_id(self.working_day["result_user_id"], self))}?\n'
                 f'\n'
                 f'{self.gt("voting_ended")} {user_link(find_user_by_id(self.working_day["result_user_id"], self))}!',
            parse_mode=ParseMode.HTML,
            reply_markup=None)

        await context.bot.send_message(
            self.chat_id,
            text=f'{user_link(find_user_by_id(self.working_day["result_user_id"], self))} '
                 f'{self.gt("were")} '
                 f'{self.gt(find_hero_by_user_id(self.working_day["result_user_id"], self).role_name)}',
            parse_mode=ParseMode.HTML
        )
        find_hero_by_user_id(self.working_day["result_user_id"], self).is_alive = False
        if await self.check_game_end(context):
            self.started = False
            return
        await self.start_night(context)

    async def mafia_mail_sent(self, user, text, context):
        """Функция отправляет сообщение присланное боту кем-то из мафии,
         во время ночного голосования, остальным членам группировки"""
        user_role = find_hero_by_user_id(user.id, self)

        for mafia in self.mafia_list:
            if mafia != user_role:
                await context.bot.send_message(
                    mafia.user.id,
                    text=f'<b>{user.full_name}:</b>\n'
                         f'{text}',
                    parse_mode=ParseMode.HTML)

    async def user_sent_last_message(self, user_role, text, context):
        """Объявляет чату предсмертное письмо игрока"""
        self.all_sent_messages.append(await context.bot.send_message(
            self.chat_id,
            text=f'{self.gt("someone_heard")} {user_link(user_role.user)} {self.gt("screamed_before_death")}:\n'
                 f'{text}'))

    async def delete_all_game_messages(self):
        """Удаляет все сообщения игры"""
        for mes in self.all_sent_messages:
            await mes.delete()

    async def change_don(self, context):
        """Назначает нового Дона мафии, и сообщает об этом членам мафии"""
        old_mafia = random.choice(self.mafia_list)
        new_don = Don(self, old_mafia.user)
        self.mafia_list[self.mafia_list.index(old_mafia)] = new_don
        self.heroes[self.heroes.index(old_mafia)] = new_don

        for mafia in self.mafia_list:
            if mafia.is_alive:
                await context.bot.send_message(mafia.user.id,
                                               text=f'{user_link(mafia.user)} - {self.gt("new")} '
                                                    f'{self.gt("don_role_name_short")}',
                                               parse_mode=ParseMode.HTML)

    async def send_alive_users_night_var(self, context):
        """Отправляет список живых игроков в начале ночи"""
        heroes = get_alive_heroes(self.heroes)
        alive_users = alive_users_str_list(heroes)

        await context.bot.send_message(self.chat_id,
                                       text=f'<b>{self.gt("Живые игроки: ")}</b>\n'
                                            f'{alive_users}\n'
                                            f'\n'
                                            f'{self.gt("sleep_left")} '
                                            f'{parse_seconds(self.settings["timings"]["night"], self)}',
                                       parse_mode=ParseMode.HTML)

    async def send_alive_users_day_var(self, context):
        """Отправляет список живых игроков и ролей в начале дня"""
        heroes = get_alive_heroes(self.heroes)
        alive_users = alive_users_str_list(heroes)

        await context.bot.send_message(self.chat_id,
                                       text=f'<b>{self.gt("Живые игроки: ")}</b>\n'
                                            f'{alive_users}\n'
                                            f'\n'
                                            f'<b>{self.gt("someone_from_them")}:</b>\n'
                                            f'{get_heroes_counts(heroes)}\n'
                                            f'{self.gt("total_var_2")}: {len(heroes)} {self.gt("people_short")}\n'
                                            f'\n'
                                            f'{self.gt("its_time_to_day_talk")}',
                                       parse_mode=ParseMode.HTML)
