from svgtopath import svg_to_path_data
from pypinyin import pinyin, Style

import os
import shutil
import json
import secrets
import requests
import time
from datetime import datetime, timezone, timedelta

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
        2:  ('103', '153'),
        3:  ('104', '104'),
        45: ('501', '501'), 
        48: ('501', '501'),
        51: ('309', '309'),
        53: ('309', '309'),
        55: ('305', '305'),
        56: ('313', '313'),
        57: ('313', '313'),
        61: ('305', '305'),
        63: ('306', '306'),
        65: ('307', '307'),
        66: ('313', '313'),
        67: ('313', '313'),
        71: ('400', '400'),
        73: ('401', '401'),
        75: ('402', '402'),
        77: ('407', '407'),
        80: ('300', '350'),
        81: ('300', '350'),
        82: ('301', '351'),
        85: ('407', '457'),
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
    load_template('choosepage')
    load_template('choosepage/letter_card')
    load_template('choosepage/item')
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
            icon_cache[qwid] = svg_to_path_data(requests.get(f'https://gh-proxy.org/https://raw.githubusercontent.com/qwd/Icons/refs/heads/main/icons/{qwid}.svg').text, merge=True)
        return icon_cache[qwid]
        
    icon_cache = {}
    print('weatherpage-开始')
    print('weatherpage-加载模板')
    load_template('weatherpage')
    load_template('weatherpage/7d')
    load_template('weatherpage/24h')
    weather_api_url_head = 'https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}{attr}'
    weather_api_url_attr = \
    '&current='\
        'temperature_2m,'\
        'relative_humidity_2m,'\
        'weather_code,'\
        'wind_speed_10m,'\
        'is_day,'\
        'apparent_temperature,'\
        'cloud_cover'\
    '&hourly='\
        'temperature_2m,'\
        'weather_code,'\
        'wind_speed_10m,'\
        'relative_humidity_2m,'\
        'is_day,'\
        'uv_index'\
    '&daily='\
        'relative_humidity_2m_mean,'\
        'weather_code,'\
        'temperature_2m_max,'\
        'temperature_2m_min,'\
        'wind_speed_10m_mean,'\
        'sunrise,'\
        'sunset'\
    '&timezone=Asia%2FShanghai'\
    '&timeformat=unixtime'\
    '&forecast_hours=24'\
    
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
        weather_r = requests.get(full_weather_api_url)
        weather_r.raise_for_status()
        weather_api_data = weather_r.json()
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
            'now_wind': cwd['current']['wind_speed_10m'],
            'attr1_sunrise': ts_to_text(cwd['daily']['sunrise'][0], '%H:%M'),
            'attr1_sunset': ts_to_text(cwd['daily']['sunset'][0], '%H:%M'),
            '24h': '\n'.join([
                replaces(templates['weatherpage/24h'],{
                    'time': ts_to_text(cwd['hourly']['time'][hour], '%H:%M'),
                    'temp': round(cwd['hourly']['temperature_2m'][hour]),
                    'weather_text': wmocode_to_text(cwd['hourly']['weather_code'][hour]),
                    'weather_icon': get_icon(icon_qwid(cwd['hourly']['weather_code'][hour], cwd['hourly']['is_day'][hour])),
                    'wind': cwd['hourly']['wind_speed_10m'][hour],
                    'humi': cwd['hourly']['relative_humidity_2m'][hour],
                }) for hour in range(len(list(cwd['hourly']['time']))) # type: ignore
            ]),
            '7d': '\n'.join([
                replaces(templates['weatherpage/7d'],{
                    'date': ts_to_text(cwd['daily']['time'][day], '%m/%d'),
                    'temp_max': round(cwd['daily']['temperature_2m_max'][day]),
                    'temp_min': round(cwd['daily']['temperature_2m_min'][day]),
                    'weather_text': wmocode_to_text(cwd['daily']['weather_code'][day]),
                    'weather_icon': get_icon(icon_qwid(cwd['daily']['weather_code'][day])),
                    'wind': cwd['daily']['wind_speed_10m_mean'][day],
                    'humi': cwd['daily']['relative_humidity_2m_mean'][day],
                }) for day in range(len(list(cwd['daily']['time']))) # type: ignore
            ]),
            'sponsors':'\n'.join([replaces(templates['sponsors'],{
                'sponsor': s
            }) for s in sponsors])
        })
        print('weatherpage-保存输出文件')
        save_output_file(f'{locations[index]['id']}.xaml',output)
        save_output_file(f'{locations[index]['id']}.xaml.ini',BUILD_VERSION)

def init():
    print('init-初始化中')
    global OUTPUT_PATH, BASE_PATH, BUILD_VERSION, templates, ncm, test_environment, data, sponsors
    templates = {}
    data = {}
    BUILD_VERSION = secrets.token_hex(4)
    BASE_PATH = os.path.dirname(__file__)
    OUTPUT_PATH = os.path.join(BASE_PATH,'output')
    shutil.rmtree(OUTPUT_PATH,ignore_errors=True)
    os.makedirs(OUTPUT_PATH,exist_ok=True)
    os.makedirs(os.path.join(BASE_PATH,'data'),exist_ok=True)
    sponsors = requests.get('https://v4.gh-proxy.org/https://github.com/wzyaeu/IfadianSponsorGet/raw/refs/heads/pagedata/output.json').json()

    test_environment = os.path.exists(os.path.join(BASE_PATH,'test_environment'))

    print('init-运行choosepage')
    choosepage()

    print('init-运行weatherpage')
    weatherpage()

init()