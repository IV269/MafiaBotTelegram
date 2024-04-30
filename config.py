BOT_TOKEN = '6992766350:AAEDlMW8HU2zJ2Vp8y4FIuIqvXDbCWlz6SQ'
BOT_LINK = 'https://t.me/VeryCollMafiaBot'
"""Изначальные настройки игры"""
DEFAULT_SETTINGS = {
    'timings': {
        'checkin': 15,
        'night': 15,
        'day': 15,
        'day_voting': 30,
        'day_vote_check': 30
    },
    'roles': {
        'doctor': True,
        'don': True,
        'investigator': True,
        'mistress': True,
        'sheriff': True,
        'lucky': True
    },
    'other': {
        'emoji_use': True
    },
    'mode': 'default',
    'language': 'ru'
}
SUPPORTED_LANGUAGES = ['ru', 'en']  # Возможные языки
NUM_OF_SUPPORTED_LANGUAGES = len(SUPPORTED_LANGUAGES)
CITIES = [
    {
        'title': 'Венеция',
        'description': 'Венеция - город в Италии, расположенный более чем на 100 небольших островах.'
                       ' Здесь совсем нет дорог, движение происходит только по каналам!',
        'coords': (45,4371, 12,3327)
    },
    {
        'title': 'Нью-Йорк',
        'description': 'Нью-Йорк - крупнейший город США, город-небоскрёб.'
                       ' Является очень важным финансовым, политическим, экономическим и культурным центром мира!',
        'coords': (40.7143, -74.006)
    },
]