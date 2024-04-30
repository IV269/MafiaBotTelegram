import i18n
import emoji
import hashlib
import json
from config import DEFAULT_SETTINGS


class Tree:
    def __init__(self, data):
        self.data = data
        self.children = {}

    def add_node(self, obj):
        node = SettingsNode(obj, self, [obj])
        self.children[obj] = node
        return node


class SettingsNode:
    def __init__(self, data, parent, key_list):
        self.data = data
        self.children = {}
        self.parent = parent
        self.key_list = key_list

    def add_node(self, obj):
        node = SettingsNode(obj, self, self.key_list + [obj])
        self.children[obj] = node
        return node


# Задание статичных настроек locales
i18n.load_path.append('./locales')
i18n.set('filename_format', '{locale}.{format}')
i18n.set('skip_locale_root_data', True)
i18n.set('file_format', 'json')


def build_tree_branch(branch, key_list, branch_dict):
    if type(branch_dict) == dict:
        for key in branch_dict.keys():
            new_branch = branch.add_node(key)
            if type(branch_dict[key]) == dict:
                build_tree_branch(new_branch, key_list + [key], branch_dict[key])
            else:
                new_branch.property = branch_dict[key]
                new_branch.key_list = key_list + [key]
                new_branch.property.settings_key_list = key_list + [key]
    else:
        branch.property = branch_dict
        branch.key_list = key_list
        branch.property.settings_key_list = key_list


def build_settings_tree(root, tree_dict):
    tree = Tree(root)
    for key in tree_dict.keys():
        new_branch = tree.add_node(key)
        build_tree_branch(new_branch, [key], tree_dict[key])
    return tree


def get_i18n_settings(settings):
    return {
        'language': settings['language'],
        'other': {'emoji_use': settings['other']['emoji_use']},
        'mode': settings['mode']
    }


def gt(key, settings, **kwargs):
    """Основываясь на настройках возвращает текст соответсвующий ключу key"""
    i18n.set('locale', f"{settings['mode']}_{settings['language']}_{['raw', 'emoji'][settings['other']['emoji_use']]}")
    i18n.set('fallback', f"service_{settings['language']}_{settings['mode']}")
    return emoji.emojize(i18n.t(key, **kwargs))


def parse_command(text, command):
    """Возвращает переданный в команде параметр"""
    return text[1 + len(command) + 1:]


def chat_id_to_game_hash(chat_id):
    """Переводит числовой идентификатор чата в строковый хэш"""
    return hashlib.md5(str(chat_id).encode()).hexdigest()


def remove_job_if_exists(name, context):
    """Удаляем задачу по имени.
    Возвращаем True если задача была успешно удалена."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def get_alive_heroes(heroes):
    """Возвращает всех живых героев"""
    return [hero for hero in heroes if hero.is_alive]


def user_link(user):
    """Возвращает ссылку на пользователя в формате HTML (при отправке сообщения необходимо задать
    параметр parse_mode равный ParseMode.HTML, взятый из telegram.constants)"""
    return f'<a href="tg://user?id={user.id}">{user.full_name}</a>'


def get_heroes_counts(heroes):
    """Возвращает живых игроков"""
    heroes_cnt = {}
    for hero in heroes:
        heroes_cnt[hero.role_name_short] = heroes_cnt.get(hero.role_name_short, 0) + 1
    heroes_alive = []
    for hero in heroes_cnt.keys():
        if heroes_cnt[hero] > 1:
            heroes_alive.append(f"{hero} - {heroes_cnt[hero]}")
        else:
            heroes_alive.append(f"{hero}")

    return ', '.join(heroes_alive)


def parse_seconds(seconds, game):
    minutes = seconds // 60
    seconds = seconds % 60
    res = ''

    if minutes > 0:
        res += f'{minutes} {game.gt("minutes_short")} '
    if seconds > 0:
        res += f'{seconds} {game.gt("seconds_short")}'

    return res


def alive_users_str_list(heroes):
    return '\n'.join([f"{i + 1}. {user_link(heroes[i].user)}" for i in range(len(heroes))])


def plural_seconds_ru(cnt):
    words = ["секунда", "секунды", "секунд"]

    if all((cnt % 10 == 1, cnt % 100 != 11)):
        return words[0]
    elif all((2 <= cnt % 10 <= 4,
              any((cnt % 100 < 10, cnt % 100 >= 20)))):
        return words[1]
    return words[2]


def find_user_by_id(user_id, game):
    """Находим пользователя по id"""
    return list(filter(lambda x: x.id == user_id, game.users))[0]


def find_hero_by_user_id(user_id, game):
    """Находим человека по его id"""
    return list(filter(lambda x: x.user.id == user_id, game.heroes))[0]


def find_hero_by_role(role, game):
    """Находим человека по его роли"""
    res = list(filter(lambda x: type(x).__name__ == role.capitalize(), game.heroes))
    if res:
        return res[0]


def parse_inline_keyboard_select_user(query, context):
    data_list = json.loads(query.data)
    game = context.bot_data[data_list[1]]
    # Находим героя, который проголосовал и игрока, который был выбран
    return data_list, game, \
           find_hero_by_user_id(query.from_user.id, game), \
           find_user_by_id(data_list[2], game)


def calculate_roles(users_count, settings):
    """Считаем, какие роли нужны с учётом настроек и количества игрков для данной игры, и возвращаем список"""
    roles = []
    if settings['roles']['don']:
        roles.append('don')
    for i in range(users_count // 3 - roles.count('don')):
        roles.append('mafia')
    if settings['roles']['doctor'] and users_count >= 3:
        roles.append('doctor')
    if settings['roles']['lucky'] and users_count >= 4:
        roles.append('lucky')
    if settings['roles']['investigator'] and users_count >= 5:
        roles.append('investigator')
    # if settings['roles']['sheriff'] and users_count >= 8:
    #     roles.append('sheriff')
    roles.append('citizen' * (users_count - len(roles)))
    return roles


def get_chat_settings(context):
    if 'settings' in context.chat_data.keys():
        return context.chat_data['settings']
    else:
        return DEFAULT_SETTINGS


def chat_gt(key, context, **kwargs):
    return gt(key, get_i18n_settings(get_chat_settings(context)), **kwargs)


def emoji_checkbox(value):
    if value:
        return emoji.emojize(':check_mark_button:')
    else:
        return emoji.emojize(':white_large_square:')


def get_chat_property(key_list, context):
    value = get_chat_settings(context)

    for i in range(len(key_list)):
        value = value[key_list[i]]

    return value


def get_mafia_cnt(game):
    return len(list(filter(lambda x: x.is_alive is True, game.mafia_list)))


def if_game_end(game):
    alive_mafia_cnt = get_mafia_cnt(game)
    if alive_mafia_cnt == 0:
        return 'citizens'
    elif alive_mafia_cnt == len(game.heroes) - alive_mafia_cnt:
        return 'mafia'

def find_3_max_rating_values(rating):
    listed = list(map(lambda x: x['wins'], rating))
    print(listed)
    return sorted(list(set(listed)), reverse=True, key=lambda x: x)[:3]

def parse_rating(group_rating):
    print(group_rating)
    res = []
    group_rating.sort(key=lambda x: x['wins'], reverse=True)
    for gamer in group_rating:
        res.append(f"{user_link(gamer['user'])} - {gamer['wins']}")

    largest = find_3_max_rating_values(group_rating)
    for i in range(len(group_rating)):
        res[i] = emoji.emojize(
            [':1st_place_medal: ', ':2nd_place_medal: ', ':3rd_place_medal: '][largest.index(group_rating[i]['wins'])]
        + res[i])

    # value = group_rating[0]['wins']
    # tmp = value
    # i = 0
    # print(res)
    # while value == tmp and i < len(res):
    #     res[i] = emoji.emojize(':1st_place_medal: ' + res[i])
    #     i += 1
    #     value = group_rating[i]['wins']
    # if i < len(res):
    #     value = group_rating[i]['wins']
    #     tmp = value
    #     i = 0
    #     while value == tmp and i < len(res):
    #         res[i] = emoji.emojize(':2nd_place_medal: ' + res[i])
    #         i += 1
    #         value = group_rating[i]['wins']
    # if i < len(res):
    #     value = group_rating[i]['wins']
    #     tmp = value
    #     i = 0
    #     while value == tmp and i < len(res):
    #         res[i] = emoji.emojize(':3rd_place_medal: ' + res[i])
    #         i += 1
    #         value = group_rating[i]['wins']
    return '\n'.join(res)


def find_heroes_by_team(team_name, game):
    return list(filter(lambda x: x.team == team_name, game.heroes))

def get_alive_heroes_in_team(team_name, game):
    return list(filter(lambda x: x.team == team_name and x.is_alive, game.heroes))


def heroes_list_to_str(heroes, game):
    res = []

    for hero in heroes:
        res.append(f"    {user_link(hero.user)} - {game.gt(hero.role_name_short)}")

    return '\n'.join(res)

def game_ended_message(won_team, game):
    won_text = {
        'citizens': 'citizens_won',
        'mafia': 'mafia_won'
    }
    return f"<b>{game.gt('game_ended')}</b>\n" \
           f"{game.gt(won_text[won_team])}\n" \
           f"\n" \
           f"{game.gt('won')}:\n" \
           f"{heroes_list_to_str(get_alive_heroes_in_team(won_team, game), game)}"
