import json
from math import ceil
from datetime import datetime, timedelta
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from utils import build_settings_tree, emoji_checkbox, get_chat_property, chat_gt, gt, get_i18n_settings
from config import SUPPORTED_LANGUAGES, NUM_OF_SUPPORTED_LANGUAGES


class BooleanProperty:
    def __init__(self, property_key, description_key, true_option_key, false_option_key, title_key=None,
                 i18n_placeholders=None):
        if i18n_placeholders is None:
            i18n_placeholders = {}
        self.description_key = description_key
        self.true_option_key = true_option_key
        self.false_option_key = false_option_key
        self.title_key = title_key
        self.settings_key_list = None
        self.property_key = property_key
        self.i18n_placeholders = i18n_placeholders

    def gettext(self, key, context):
        for placeholder in self.i18n_placeholders.keys():
            if type(self.i18n_placeholders[placeholder]) == dict:
                self.i18n_placeholders[placeholder] = chat_gt(self.i18n_placeholders[placeholder]['key'], context)
        return chat_gt(key, context, **self.i18n_placeholders)

    def get_message(self, context):
        text = ''
        if self.title_key:
            text += f'<b>{self.gettext(self.title_key, context)}</b>\n'
        text += self.gettext(self.description_key, context)
        value = get_chat_property(self.settings_key_list, context)

        return {
            'text': text,
            'reply_markup': InlineKeyboardMarkup([
                [InlineKeyboardButton(text=f'{self.gettext(self.true_option_key, context)}  '
                                           f'{emoji_checkbox(value)}',
                                      callback_data=json.dumps([
                                          'chat settings update',
                                          self.settings_key_list,
                                          True
                                      ]))],
                [InlineKeyboardButton(text=f'{self.gettext(self.false_option_key, context)}  '
                                           f'{emoji_checkbox(not value)}',
                                      callback_data=json.dumps([
                                          'chat settings update',
                                          self.settings_key_list,
                                          False
                                      ]))],
                [InlineKeyboardButton(text=chat_gt('back', context),
                                      callback_data=json.dumps([
                                          'chat settings clicked',
                                          'back'
                                      ]))]
            ]),
            'parse_mode': ParseMode.HTML
        }


class SecondsProperty:
    def __init__(self, property_key, description_key, title_key=None, i18n_placeholders=None):
        if i18n_placeholders is None:
            i18n_placeholders = {}
        self.seconds_options = [30, 45, 60, 75, 90, 120, 180, 240, 300, 360]
        self.description_key = description_key
        self.title_key = title_key
        self.settings_key_list = None
        self.property_key = property_key
        self.i18n_placeholders = i18n_placeholders

    def gettext(self, key, context):
        for key in self.i18n_placeholders.keys():
            if type(self.i18n_placeholders[key]) == dict:
                self.i18n_placeholders[key] = chat_gt(key, context)
        return chat_gt(key, context, **self.i18n_placeholders)

    def get_message(self, context):
        text = ''
        if self.title_key:
            text += f'<b>{self.gettext(self.title_key, context)}</b>\n'
        text += self.gettext(self.description_key, context)
        value = get_chat_property(self.settings_key_list, context)
        keyboard = []
        h = len(self.seconds_options) // 2

        for i in range(h):
            keyboard.append([
                InlineKeyboardButton(text=f'{self.seconds_options[i]}  '
                                          f'{emoji_checkbox(value == self.seconds_options[i])}',
                                     callback_data=json.dumps([
                                         'chat settings update',
                                         self.settings_key_list,
                                         self.seconds_options[i]
                                     ])),
                InlineKeyboardButton(text=f'{self.seconds_options[i + h]}  '
                                          f'{emoji_checkbox(value == self.seconds_options[i + h])}',
                                     callback_data=json.dumps([
                                         'chat settings update',
                                         self.settings_key_list,
                                         self.seconds_options[i + h]
                                     ]))
            ])
        keyboard.append([InlineKeyboardButton(text=chat_gt('back', context),
                                              callback_data=json.dumps([
                                                  'chat settings clicked',
                                                  'back'
                                              ]))])

        return {
            'text': text,
            'reply_markup': InlineKeyboardMarkup(keyboard),
            'parse_mode': ParseMode.HTML
        }


class LanguageProperty:
    def get_locale_name(self, iso_code, context):
        i18n_settings = get_i18n_settings(context.chat_data['settings'])
        i18n_settings['language'] = iso_code
        text = gt('language_name', i18n_settings)
        return text

    def get_message(self, context):
        value = get_chat_property(['language'], context)
        keyboard = []
        h = ceil(NUM_OF_SUPPORTED_LANGUAGES / 2)
        i18n_settings = get_i18n_settings(context.chat_data['settings'])
        text = chat_gt('choose_language', context)
        if i18n_settings['language'] != 'en':
            i18n_settings['language'] = 'en'
            text += ' / ' + gt('choose_language', i18n_settings)

        for i in range(h):
            row = [
                InlineKeyboardButton(text=f'{self.get_locale_name(SUPPORTED_LANGUAGES[i], context)}  '
                                          f'{emoji_checkbox(value == SUPPORTED_LANGUAGES[i])}',
                                     callback_data=json.dumps([
                                         'chat settings update',
                                         ['language'],
                                         SUPPORTED_LANGUAGES[i]
                                     ]))]
            if i + 1 < NUM_OF_SUPPORTED_LANGUAGES:
                row.append(
                    InlineKeyboardButton(text=f'{self.get_locale_name(SUPPORTED_LANGUAGES[i + 1], context)}  '
                                              f'{emoji_checkbox(value == SUPPORTED_LANGUAGES[i + 1])}',
                                         callback_data=json.dumps([
                                             'chat settings update',
                                             ['language'],
                                             SUPPORTED_LANGUAGES[i + 1]
                                         ])))
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton(text=chat_gt('back', context),
                                              callback_data=json.dumps([
                                                  'chat settings clicked',
                                                  'back'
                                              ]))])

        return {
            'text': text,
            'reply_markup': InlineKeyboardMarkup(keyboard),
            'parse_mode': ParseMode.HTML
        }


class ChatSettings:
    def __init__(self, user_id, chat, chat_context):
        self.user_id = user_id
        self.chat = chat
        self.chat_context = chat_context
        self.menu_tree = CHAT_SETTINGS_TREE
        self.now_stage = self.menu_tree
        self.active_until = datetime.utcnow() + timedelta(hours=24)
        self.message = None

    def check_is_active(self):
        return datetime.utcnow() < self.active_until

    def button_text(self, key, context):
        if key == 'language':
            text = chat_gt('language', context)
            i18n_settings = get_i18n_settings(context.chat_data['settings'])
            if i18n_settings['language'] != 'en':
                i18n_settings['language'] = 'en'
                text += ' / ' + gt('language_no_flag', i18n_settings)
            return text
        else:
            return chat_gt(key, context)

    def gen_now_page(self):
        if self.now_stage.data == 'settings_main_page':
            return {
                'text': f'{chat_gt("what_settings_edit_in_group", self.chat_context)} <b>{self.chat.title}</b>?',
                'reply_markup': InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text=self.button_text('.'.join(item.key_list), self.chat_context),
                                           callback_data=json.dumps([
                                               'chat settings clicked',
                                               item.data
                                           ]))
                      ] for item in self.menu_tree.children.values()
                     ] + [[InlineKeyboardButton(text=chat_gt('exit', self.chat_context),
                                                callback_data=json.dumps([
                                                    'chat settings clicked',
                                                    'exit'
                                                ]))]]),
                'parse_mode': ParseMode.HTML
            }
        elif len(self.now_stage.children.keys()):
            return {
                'text': chat_gt(f'what_{self.now_stage.data}_edit', self.chat_context),
                'reply_markup': InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text=item.property.gettext(item.property.property_key, self.chat_context),
                                           callback_data=json.dumps([
                                               'chat settings clicked',
                                               item.data
                                           ]))]
                     for item in self.now_stage.children.values()] + [
                        [InlineKeyboardButton(text=chat_gt('back', self.chat_context),
                                              callback_data=json.dumps([
                                                  'chat settings clicked',
                                                  'back'
                                              ]))]
                    ])
            }
        else:
            return self.now_stage.property.get_message(self.chat_context)

    async def send_message(self, context):
        self.message = await context.bot.send_message(self.user_id,
                                                      **self.gen_now_page())

    async def update_message(self):
        await self.message.edit_text(**self.gen_now_page())

    async def move_to(self, dest):
        if self.check_is_active():
            self.now_stage = self.now_stage.children[dest]
            await self.update_message()

    async def move_back(self):
        if self.check_is_active():
            self.now_stage = self.now_stage.parent
            await self.update_message()

    async def exit(self):
        await self.message.edit_text(text=chat_gt('settings_saved', self.chat_context),
                                     parse_mode=ParseMode.HTML)
        self.chat_context.user_data['chat_settings'] = None


CHAT_SETTINGS_TREE_DICT = {
    'roles': {
        'doctor': BooleanProperty('role_property_name', 'include_role', 'yes', 'no', i18n_placeholders={
            'role_short_name': {
                'key': 'roles.doctor'
            }
        }),
        'don': BooleanProperty('role_property_name', 'include_role', 'yes', 'no', i18n_placeholders={
            'role_short_name': {
                'key': 'roles.don'
            }
        }),
        'investigator': BooleanProperty('role_property_name', 'include_role', 'yes', 'no', i18n_placeholders={
            'role_short_name': {
                'key': 'roles.investigator'
            }
        }),
        # 'mistress': BooleanProperty('role_property_name', 'include_role', 'yes', 'no', i18n_placeholders={
        #     'role_short_name': {
        #         'key': 'roles.mistress'
        #     }
        # }),
        # 'sheriff': BooleanProperty('role_property_name', 'include_role', 'yes', 'no', i18n_placeholders={
        #     'role_short_name': {
        #         'key': 'roles.sheriff'
        #     }
        # }),
        # 'manyak': BooleanProperty('role_property_name', 'include_role', 'yes', 'no', i18n_placeholders={
        #     'role_short_name': {
        #         'key': 'roles.sheriff'
        #     }
        # }),
        'lucky': BooleanProperty('role_property_name', 'include_role', 'yes', 'no', i18n_placeholders={
            'role_short_name': {
                'key': 'roles.lucky'
            }
        }),
    },
    'timings': {
        'checkin': SecondsProperty('timings.checkin.property_name', 'timings.checkin.description'),
        'night': SecondsProperty('timings.night.property_name', 'timings.night.description'),
        'day': SecondsProperty('timings.day.property_name', 'timings.day.description'),
        'day_voting': SecondsProperty('timings.day_voting.property_name', 'timings.day_voting.description'),
        'day_vote_check': SecondsProperty('timings.day_vote_check.property_name', 'timings.day_vote_check.description')
    },
    'other': {
        'emoji_use': BooleanProperty('other.emoji_use', 'other.emoji_type.description', 'yes', 'no'),
    },
    # 'mode': BooleanProperty('a', 'b', 'c', 'c'),
    'language': LanguageProperty()
}
CHAT_SETTINGS_TREE = build_settings_tree('settings_main_page', CHAT_SETTINGS_TREE_DICT)


async def chat_settings_clicked(query, context):
    if 'chat_settings' in context.user_data.keys():
        if context.user_data['chat_settings'].message.id == query.message.id:
            data_list = json.loads(query.data)
            if data_list[1] == 'exit':
                await context.user_data['chat_settings'].exit()
                await query.answer(chat_gt('exit', context))
            elif data_list[1] == 'back':
                await context.user_data['chat_settings'].move_back()
                await query.answer(chat_gt(context.user_data['chat_settings'].now_stage.data, context))
            else:
                await context.user_data['chat_settings'].move_to(data_list[1])
                await query.answer(chat_gt(data_list[1], context))
    else:
        await query.message.edit_text(text=chat_gt('message_inactive', context))


async def chat_settings_update(query, context):
    if 'chat_settings' in context.user_data.keys():
        if context.user_data['chat_settings'].message.id == query.message.id:
            data_list = json.loads(query.data)
            prop = context.user_data['chat_settings'].chat_context.chat_data['settings']

            for i in range(len(data_list[1][:-1])):
                prop = prop[data_list[1][:-1][i]]

            prop[data_list[1][-1]] = data_list[2]
            await query.answer(text=chat_gt('settings_saved', context))
            await context.user_data['chat_settings'].update_message()
        else:
            await query.message.edit_text(text=chat_gt('message_inactive', context))
    else:
        await query.message.edit_text(text=chat_gt('message_inactive', context))


async def edit_chat_settings(update, context):
    settings = ChatSettings(update.effective_user.id, update.effective_chat, context)
    context.user_data['chat_settings'] = settings
    await settings.send_message(context)