import requests

default = {
    'now': 1682460918,
    'now_dt': '2023-04-25T22:15:18.559208Z',
    'info': {
        'url': 'https://yandex.ru/pogoda/2?lat=59.939&lon=30.316',
        'lat': 59.939,
        'lon': 30.316
    },
    'fact': {
        'obs_time': 1682460000,
        'temp': 12,
        'feels_like': 9,
        'temp_water': 1,
        'icon': 'skc_n',
        'condition': 'clear',
        'wind_speed': 1,
        'wind_dir': 'e',
        'pressure_mm': 753,
        'pressure_pa': 1003,
        'humidity': 31,
        'daytime': 'n',
        'polar': False,
        'season': 'spring',
        'wind_gust': 4.2
    },
    'forecast': {
        'date': '2023-04-26',
        'date_ts': 1682456400,
        'week': 17,
        'sunrise': '05:12',
        'sunset': '20:41',
        'moon_code': 11,
        'moon_text': 'moon-code-11',
        'parts': [
            {
                'part_name': 'morning',
                'temp_min': 9,
                'temp_avg': 15,
                'temp_max': 20,
                'temp_water': 1,
                'wind_speed': 2.4,
                'wind_gust': 3.8,
                'wind_dir': 'se',
                'pressure_mm': 753,
                'pressure_pa': 1003,
                'humidity': 64,
                'prec_mm': 0,
                'prec_prob': 0,
                'prec_period': 360,
                'icon': 'skc_d',
                'condition': 'partly-cloudy',
                'feels_like': 13,
                'daytime': 'd',
                'polar': False
            },
            {'part_name': 'day', 'temp_min': 21, 'temp_avg': 22, 'temp_max': 22, 'temp_water': 2, 'wind_speed': 2.9,
             'wind_gust': 4.3, 'wind_dir': 'se', 'pressure_mm': 752, 'pressure_pa': 1002, 'humidity': 36, 'prec_mm': 0,
             'prec_prob': 0, 'prec_period': 360, 'icon': 'bkn_d', 'condition': 'cloudy', 'feels_like': 19,
             'daytime': 'd', 'polar': False}
        ]}
    }

def forecast(coords):
    response = requests.get("https://api.weather.yandex.ru/v2/informers",
                            params={
                                'lat': coords[0],
                                'lon': coords[1]
                            },
                            headers={
                                'X-Yandex-API-Key': '5af80a17-a8c0-4996-b11e-cbe809ba2d13'
                            })
    return response.json()
