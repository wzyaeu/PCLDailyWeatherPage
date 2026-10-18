from svgtopath import svg_to_path_data
from pypinyin import pinyin, Style

import os
import shutil
import json
import secrets
import requests
import time
from datetime import datetime, timezone, timedelta
from typing import Literal
import math

BASE_PATH = os.path.dirname(__file__)
def load_all_template():
    global templates
    templates = {}
    templates_path = os.path.join(BASE_PATH, 'templates')
    for root, dirs, files in os.walk(templates_path):
        for file in files:
            file_path = os.path.join(root, file)
            print(f'load_template-加载模板文件-{os.path.join(root, file)}')
            name = os.path.relpath(file_path, templates_path)
            if name.endswith('.xaml'):
                name = name[:-len('.xaml')]
            name = name.replace('\\', '/')
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    templates[name] = f.read()
            except Exception as e:
                exit()

def load_template(name, noxaml = False):
    print(f'load_template-加载模板文件-{name}')
    global templates
    if not name in templates:
        t_path = os.path.join(BASE_PATH, 'templates', name+('' if noxaml else '.xaml'))
        with open(t_path,'r', encoding='utf-8') as f:
            templates[name] =  f.read()

def load_data(name):
    print(f'load_data-加载数据文件-{name}')
    global data
    if not name in templates:
        t_path = os.path.join(BASE_PATH, 'data', name)
        with open(t_path,'r', encoding='utf-8') as f:
            data['.'.join(name.split('.')[:-1])] =  f.read()

def save_output_file(name, data):
    print(f'save_output_file-保存输出文件-{name}')
    o_path = os.path.join(BASE_PATH, 'output', name)
    with open(o_path,'w', encoding='utf-8') as f:
        f.write(data)

def replaces(string: str, s: dict):
    output = string
    for l, d in s.items():
        output = output.replace('{'+l+'}', str(d))
    return output

def wind_speed_to_beaufort_scale(speed, contents: list[Literal['scale', 'cn']]):
    beaufort_scale_data = {
        'scale':{
            (lambda x: 0 <= x < 1): '0',
            (lambda x: 1 <= x < 6): '1',
            (lambda x: 6 <= x < 12): '2',
            (lambda x: 12 <= x < 20): '3',
            (lambda x: 20 <= x < 29): '4',
            (lambda x: 29 <= x < 39): '5',
            (lambda x: 39 <= x < 50): '6',
            (lambda x: 50 <= x < 62): '7',
            (lambda x: 62 <= x): '7+',
        },
        'cn':{
            (lambda x: 0 <= x < 1): '无风',
            (lambda x: 1 <= x < 6): '软风',
            (lambda x: 6 <= x < 12): '轻风',
            (lambda x: 12 <= x < 20): '微风',
            (lambda x: 20 <= x < 29): '和风',
            (lambda x: 29 <= x < 39): '清风',
            (lambda x: 39 <= x < 50): '强风',
            (lambda x: 50 <= x < 62): '疾风',
            (lambda x: 62 <= x): '强疾风',
        },
    }
    return [[ctt for cdti, ctt in beaufort_scale_data.get(content, {}).items() if cdti(speed)][0] for content in contents]

def rain_scale(rain, contents: list[Literal['scale', 'cn']]):
    beaufort_scale_data = {
        'scale':{
            (lambda x: x == 0): 0,
            (lambda x: 0 <= x < 2.5): 1,
            (lambda x: 2.5 <= x < 8): 2,
            (lambda x: 8 <= x ): 3,
        },
        'cn':{
            (lambda x: x == 0): '',
            (lambda x: 0 <= x < 0.5): '毛毛雨',
            (lambda x: 0.5 <= x < 2.5): '小雨',
            (lambda x: 2.5 <= x < 8): '中雨',
            (lambda x: 8 <= x < 16): '大雨',
            (lambda x: 16 <= x ): '	强降雨',
        },
    }
    return [[ctt for cdti, ctt in beaufort_scale_data.get(content, {}).items() if cdti(rain)][0] for content in contents]

def escape_xaml(text):
    if text is None:
        return ''
    return (
        text.replace('&', '&amp;')
             .replace('<', '&lt;')
             .replace('>', '&gt;')
             .replace(''', '&quot;')
             .replace(''', '&apos;')
    )

def ts_to_text(ts, fm):
    return datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=8))).strftime(fm)

def icon_qwid(code: int, is_day: bool = True) -> str:
    table = {
        0:  ('100', '150'),
        1:  ('102', '152'),
        2:  ('101', '151'),
        3:  ('104', '104'),
        45: ('501', '501'), 
        48: ('501', '501'),
        51: ('309', '309'),
        53: ('309', '309'),
        55: ('311', '311'),
        56: ('312', '312'),
        57: ('311', '311'),
        61: ('305', '305'),
        63: ('306', '306'),
        65: ('307', '307'),
        66: ('313', '313'),
        67: ('313', '313'),
        71: ('400', '400'),
        73: ('401', '401'),
        75: ('402', '402'),
        77: ('1040', '1040'),
        80: ('300', '350'),
        81: ('300', '350'),
        82: ('301', '351'),
        85: ('406', '456'),
        86: ('407', '457'),
        95: ('302', '302'),
        96: ('304', '304'),
        97: ('304', '304'),
        99: ('304', '304'),
    }

    d, n = table.get(code, ('999', '999'))
    return d if is_day else n

def wmocode_to_text(code: int) -> str:
    wmo_zh: dict[int, str] = {
        0: '晴',
        1: '晴间多云',
        2: '多云',
        3: '阴',
        45: '雾',
        48: '雾凇',
        51: '小毛毛雨',
        53: '毛毛雨',
        55: '大毛毛雨',
        56: '冻毛毛雨',
        57: '强冻毛毛雨',
        61: '小雨',
        63: '中雨',
        65: '大雨',
        66: '冻雨',
        67: '强冻雨',
        71: '小雪',
        73: '中雪',
        75: '大雪',
        77: '雪粒',
        80: '小阵雨',
        81: '阵雨',
        82: '强阵雨',
        85: '小阵雪',
        86: '大阵雪',
        95: '雷阵雨',
        96: '雷阵雨伴小冰雹',
        97: '雷阵雨伴冰雹',
        99: '强雷阵雨伴大冰雹',
    }
    return wmo_zh.get(code, '未知天气')

def iso_to_timestamp(iso_str):
    return int(datetime.fromisoformat(iso_str.replace('Z', '+00:00')).timestamp())

def choosepage():
    global locations
    print('choosepage-开始')
    print('choosepage-加载模板')
    print('choosepage-加载数据')
    load_data('locations.json')
    locations = {}
    for c in [{'name': k, **v} for k, v in json.loads(data['locations']).items()]:
        for l in pinyin(c['name'], style=Style.FIRST_LETTER, heteronym=True)[0]:
            letter = l.upper()
            if letter not in locations: locations[letter] = []
            locations[letter].append({**c, 'sl': '/'.join([n.upper() for n in pinyin(c['name'], style=Style.FIRST_LETTER, heteronym=False)[1]])})
    for l in locations.keys():
        locations[l] = sorted(locations[l], key=lambda x: x['sl'])
    
    print('choosepage-构建页面')
    output = replaces(templates['choosepage'],{
        'letter_card':'\n'.join([
            replaces(templates['choosepage/letter_card'],{
                'letter': l,
                'items': '\n'.join([
                    replaces(templates['choosepage/item'],{
                        'letter': l+c['sl'],
                        'name': c['name'],
                        'locaID': c['id'],
                    }) for c in locations[l]
                ])
            }) for l in sorted(list(locations.keys()))
        ]),
        'sponsors':'\n'.join([replaces(templates['sponsors'],{
            'sponsor': s
        }) for s in sponsors])
    })
    print('choosepage-保存输出文件')
    save_output_file('choose.xaml',output)
    save_output_file('choose.xaml.ini',BUILD_VERSION)

def weatherpage():
    def get_icon(qwid):
        if qwid not in icon_cache:
            print(f'weatherpage-获取icon-{qwid}')
            if os.path.exists(os.path.join(BASE_PATH, 'data', 'icon', qwid)):
                with open(os.path.join(BASE_PATH, 'data', 'icon', qwid), 'r', encoding='utf-8') as f:
                    icon_cache[qwid] = f.read()
            else:
                icon_cache[qwid] = svg_to_path_data(requests.get(f'https://gh-proxy.org/https://raw.githubusercontent.com/qwd/Icons/refs/heads/main/icons/{qwid}.svg').text, merge=True)
                os.makedirs(os.path.join(BASE_PATH, 'data', 'icon'), exist_ok=True)
                with open(os.path.join(BASE_PATH, 'data', 'icon', qwid), 'w', encoding='utf-8') as f:
                    f.write(icon_cache[qwid])
        return icon_cache[qwid]
        
    icon_cache = {}
    print('weatherpage-开始')
    print('weatherpage-加载模板')
    weather_api_url_head = 'https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}{attr}'
    weather_api_url_attr = (lambda attr: '&'+'&'.join([f'{key}={','.join(values) if type(values) == list else values}' for key, values in attr.items()]))({
        'current': [
            'temperature_2m',
            'relative_humidity_2m',
            'weather_code',
            'wind_speed_10m',
            'temperature_2m',
            'is_day',
            'apparent_temperature',
            'cloud_cover',
            'relative_humidity_2m',
        ],
        'hourly': [
            'temperature_2m',
            'weather_code',
            'wind_speed_10m',
            'relative_humidity_2m',
            'is_day',
            'uv_index',
            'rain',
        ],
        'daily': [
            'relative_humidity_2m_mean',
            'weather_code',
            'temperature_2m_max',
            'temperature_2m_min',
            'wind_speed_10m_mean',
            'sunrise',
            'sunset',
        ],
        'timezone': 'Asia%2FShanghai',
        'timeformat': 'unixtime',
        'forecast_hours': '24'
    })
    
    print('weatherpage-加载数据')
    locations = [{**ld, 'name': l} for l, ld in json.loads(data['locations']).items()]

    try:
        with open(os.path.join(BASE_PATH, 'data', 'weather_cache_time'), 'r', encoding='utf-8') as f:
            weather_cache_time = int(f.read())
    except:
        weather_cache_time = 0
    if int(time.time()) - weather_cache_time > 60*60 or\
        not os.path.exists(os.path.join(BASE_PATH, 'data', 'weather_cache.json')):
        
        full_weather_api_url = weather_api_url_head.format(
            latitude=','.join([str(c['latitude']) for c in locations]),
            longitude=','.join([str(c['longitude']) for c in locations]),
            attr=weather_api_url_attr
        )
        try:
            weather_r = requests.get(full_weather_api_url)
        except Exception as e:
            raise RuntimeError(f'weatherpage-api获取时发生错误-{e}')
        try:
            weather_r.raise_for_status()
            weather_api_data = weather_r.json()
        except Exception as e:
            raise RuntimeError(f'weatherpage-api获取时发生错误-{e}')
        with open(os.path.join(BASE_PATH, 'data', 'weather_cache.json'), 'w', encoding='utf-8') as f:
            json.dump(weather_api_data, f)
        with open(os.path.join(BASE_PATH, 'data', 'weather_cache_time'), 'w', encoding='utf-8') as f:
            f.write(str(int(time.time())))
    else:
        with open(os.path.join(BASE_PATH, 'data', 'weather_cache.json'), 'r', encoding='utf-8') as f:
            weather_api_data = json.load(f)

    now = datetime.now(timezone(timedelta(hours=8)))
    for index, cwd in enumerate(weather_api_data):
        print(f'weatherpage-构建页面-{index+1}/{len(weather_api_data)}')
        output = replaces(templates['weatherpage'],{
            'city': locations[index]['name'],
            'now_updatetime': now.strftime("%m/%d %H:%M:%S"),
            'now_weather_icon': get_icon(icon_qwid(cwd['current']['weather_code'], cwd['current']['is_day'])),
            'now_temp': round(cwd['current']['temperature_2m']),
            'now_weather': wmocode_to_text(cwd['current']['weather_code']),
            'today_temp_max': round(cwd['daily']['temperature_2m_max'][0]),
            'today_temp_min': round(cwd['daily']['temperature_2m_min'][0]),
            'now_temp_feel': round(cwd['current']['apparent_temperature']),
            'now_uv': cwd['hourly']['uv_index'][0],
            'now_humi': cwd['current']['relative_humidity_2m'],
            'now_cloud': cwd['current']['cloud_cover'],
            'now_wind_scale': wind_speed_to_beaufort_scale(cwd['current']['wind_speed_10m'], ['scale'])[0],
            'now_wind_text': wind_speed_to_beaufort_scale(cwd['current']['wind_speed_10m'], ['cn'])[0],
            'now_wind_speed': cwd['current']['wind_speed_10m'],
            'now_humi': cwd['current']['relative_humidity_2m'],
            'attr1_sunrise': ts_to_text(cwd['daily']['sunrise'][0], '%H:%M'),
            'attr1_sunset': ts_to_text(cwd['daily']['sunset'][0], '%H:%M'),
            'template': replaces(templates['weatherpage/template'],{
                '7dw': '\n'.join([
                    replaces(templates['weatherpage/7d/item'],{
                        'date': ts_to_text(cwd['daily']['time'][day], '%m/%d'),
                        'temp_max': round(cwd['daily']['temperature_2m_max'][day]),
                        'temp_min': round(cwd['daily']['temperature_2m_min'][day]),
                        'weather_text': wmocode_to_text(cwd['daily']['weather_code'][day]),
                        'weather_icon': get_icon(icon_qwid(cwd['daily']['weather_code'][day])),
                        'wind_scale': wind_speed_to_beaufort_scale(cwd['daily']['wind_speed_10m_mean'][day], ['scale'])[0],
                        'wind_text': wind_speed_to_beaufort_scale(cwd['daily']['wind_speed_10m_mean'][day], ['cn'])[0],
                        'wind_speed':cwd['daily']['wind_speed_10m_mean'][day],
                        'humi': cwd['daily']['relative_humidity_2m_mean'][day],
                    }) for day in range(len(list(cwd['daily']['time']))) # type: ignore
                ]),

                '24hw': '\n'.join([replaces(templates['weatherpage/24h/weather'],{
                    'time': ts_to_text(cwd['hourly']['time'][hour], '%H:%M'),
                    'temp': round(cwd['hourly']['temperature_2m'][hour]),
                    'border_radius': '5,0,0,5' if index == 0 else ('0,5,5,0' if index == hourlylen-1 else '0'),
                    'weather_text': wmocode_to_text(cwd['hourly']['weather_code'][hour]),
                    'weather_icon': get_icon(icon_qwid(cwd['hourly']['weather_code'][hour], cwd['hourly']['is_day'][hour])),
                    'wind_scale': wind_speed_to_beaufort_scale(cwd['hourly']['wind_speed_10m'][hour], ['scale'])[0],
                    'wind_text': wind_speed_to_beaufort_scale(cwd['hourly']['wind_speed_10m'][hour], ['cn'])[0],
                    'wind_speed':cwd['hourly']['wind_speed_10m'][hour],
                    'humi': cwd['hourly']['relative_humidity_2m'][hour],
                    'uv': cwd['hourly']['uv_index'][hour]
                }) for index, hour in enumerate(range(len(list(cwd['hourly']['time'])))) if (hourlylen := len(list(cwd['hourly']['time'])))]),
                '24hr_max':(rain_max := (math.ceil(max(cwd['hourly']['rain']) / 0.5) * 0.5 if max(cwd['hourly']['rain']) > 0 else 0.0)),
                '24hr_median':rain_max / 2,
                '24hr': '\n'.join([replaces(templates['weatherpage/24h/rain'],{
                    'time': ts_to_text(cwd['hourly']['time'][hour], '%H:%M'),
                    'rain': cwd['hourly']['rain'][hour],
                    'h': round(80/rain_max*cwd['hourly']['rain'][hour], 1) if rain_max > 0 else 0
                }) for index, hour in enumerate(range(len(list(cwd['hourly']['time']))))]),
            }),
            'sponsors':'\n'.join([replaces(templates['sponsors'],{
                'sponsor': s
            }) for s in sponsors])
        })
        print('weatherpage-保存输出文件')
        save_output_file(f'{locations[index]['id']}.xaml',output)
        save_output_file(f'{locations[index]['id']}.xaml.ini',BUILD_VERSION)

def init():
    load_all_template()
    print('init-初始化中')
    global OUTPUT_PATH, BASE_PATH, BUILD_VERSION, templates, ncm, test_environment, data, sponsors
    templates = {}
    data = {}
    BUILD_VERSION = secrets.token_hex(4)
    OUTPUT_PATH = os.path.join(BASE_PATH,'output')
    shutil.rmtree(OUTPUT_PATH,ignore_errors=True)
    os.makedirs(OUTPUT_PATH,exist_ok=True)
    os.makedirs(os.path.join(BASE_PATH,'data'),exist_ok=True)
    sponsors = requests.get('https://v4.gh-proxy.org/https://github.com/wzyaeu/IfadianSponsorGet/raw/refs/heads/pagedata/output.json').json()

    test_environment = os.path.exists(os.path.join(BASE_PATH,'test_environment'))

    load_all_template()

    print('init-运行choosepage')
    choosepage()

    print('init-运行weatherpage')
    weatherpage()

init()