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
from pprint import pprint
from decimal import Decimal, ROUND_HALF_UP

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

def _round(number, ndigits=0):
    if ndigits < 0:
        ndigits = 0

    d = Decimal(str(number))
    rounded = d.quantize(
        Decimal('1e-{}'.format(ndigits)),
        rounding=ROUND_HALF_UP
    )
    return float(rounded) if ndigits != 0 else int(rounded)

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

def line_chart(htdata, index):
    tmax = max(htdata)
    tmin = min(htdata)
    if tmax-tmin < 3:
        tmin = tmin - (3 - (tmax-tmin))
    hpt = 40/(tmax-tmin)
    # l1
    if index != 0:
        l1_y = (htdata[index]-htdata[index-1])/2*hpt
        l1_mag = (min(htdata[index], abs(htdata[index]-htdata[index-1])/2+min(htdata[index], htdata[index-1]))-tmin)*hpt+5
        l1_vis = 'Visible'
    else:
        l1_y = 0
        l1_mag = 0
        l1_vis = 'Collapsed'
    # l2
    if index != len(htdata)-1:
        l2_y = (htdata[index+1]-htdata[index])/2*hpt
        l2_mag = (min(htdata[index], abs(htdata[index+1]-htdata[index])/2+min(htdata[index], htdata[index+1]))-tmin)*hpt+5
        l2_vis = 'Visible'
    else:
        l2_y = 0
        l2_mag = 0
        l2_vis = 'Collapsed'
    # lc
    l_c_r = htdata[index] / tmax 
    return {
        'l1_y': l1_y,
        'l1_mag': l1_mag,
        'l1_vis': l1_vis,
        'l2_y': l2_y,
        'l2_mag': l2_mag,
        'l2_vis': l2_vis,
        'l_c': l_c_r
    }

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
    global statisticsdata
    statisticsdata = {
        'now': {
            'temp': {
                'max': (0, None),
                'min': (0, None),
            },
            'wind': (0, None),
            'weather': {

            }
        },
        'today': {
            'temp': {
                'max': (0, None),
                'min': (0, None),
            },
            'tempdiff': ((0, 0), None),
            'wind': (0, None),
            'weather': {

            }
        }
    }

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
            json.dump(weather_api_data, f, ensure_ascii=False)
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
            'now_temp': _round(cwd['current']['temperature_2m']),
            'now_weather': wmocode_to_text(cwd['current']['weather_code']),
            'today_temp_max': _round(cwd['daily']['temperature_2m_max'][0]),
            'today_temp_min': _round(cwd['daily']['temperature_2m_min'][0]),
            'now_temp_feel': _round(cwd['current']['apparent_temperature']),
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
                        'temp_max': _round(cwd['daily']['temperature_2m_max'][day]),
                        'temp_min': _round(cwd['daily']['temperature_2m_min'][day]),
                        'weather_text': wmocode_to_text(cwd['daily']['weather_code'][day]),
                        'weather_icon': get_icon(icon_qwid(cwd['daily']['weather_code'][day])),
                        'wind_scale': wind_speed_to_beaufort_scale(cwd['daily']['wind_speed_10m_mean'][day], ['scale'])[0],
                        'wind_text': wind_speed_to_beaufort_scale(cwd['daily']['wind_speed_10m_mean'][day], ['cn'])[0],
                        'wind_speed':cwd['daily']['wind_speed_10m_mean'][day],
                        'humi': cwd['daily']['relative_humidity_2m_mean'][day],
                    }) for day in range(len(list(cwd['daily']['time']))) # type: ignore
                ]),
                'htdata': (htdata := list(cwd['hourly']['temperature_2m'])[:24]) ,
                '24hw': '\n'.join([replaces(templates['weatherpage/24h/weather'],{
                    'time': ts_to_text(cwd['hourly']['time'][hour], '%H:%M'),
                    'temp': _round(cwd['hourly']['temperature_2m'][hour]),
                    'border_radius': '5,0,0,5' if index == 0 else ('0,5,5,0' if index == hourlylen-1 else '0'),
                    'weather_text': wmocode_to_text(cwd['hourly']['weather_code'][hour]),
                    'weather_icon': get_icon(icon_qwid(cwd['hourly']['weather_code'][hour], cwd['hourly']['is_day'][hour])),
                    'wind_scale': wind_speed_to_beaufort_scale(cwd['hourly']['wind_speed_10m'][hour], ['scale'])[0],
                    'wind_text': wind_speed_to_beaufort_scale(cwd['hourly']['wind_speed_10m'][hour], ['cn'])[0],
                    'wind_speed':cwd['hourly']['wind_speed_10m'][hour],
                    'humi': cwd['hourly']['relative_humidity_2m'][hour],
                    'uv': cwd['hourly']['uv_index'][hour],
                    '': (line_chart_data := line_chart(htdata, index)),
                    'l1_y': line_chart_data['l1_y'],
                    'l1_mag': line_chart_data['l1_mag'],
                    'l1_vis': line_chart_data['l1_vis'],
                    'l2_y': line_chart_data['l2_y'],
                    'l2_mag': line_chart_data['l2_mag'],
                    'l2_vis': line_chart_data['l2_vis'],
                    'l_c': line_chart_data['l_c']
                }) for index, hour in enumerate(range(len(list(cwd['hourly']['time'])[:24]))) if (hourlylen := len(list(cwd['hourly']['time'])))]),
                '24hr_max':(rain_max := (math.ceil(max(cwd['hourly']['rain']) / 0.5) * 0.5 if max(cwd['hourly']['rain']) > 0 else 0.0)),
                '24hr_median':rain_max / 2,
                '24hr': '\n'.join([replaces(templates['weatherpage/24h/rain'],{
                    'time': ts_to_text(cwd['hourly']['time'][hour], '%H:%M'),
                    'rain': cwd['hourly']['rain'][hour],
                    'h': _round(80/rain_max*cwd['hourly']['rain'][hour], 1) if rain_max > 0 else 0
                }) for index, hour in enumerate(range(len(list(cwd['hourly']['time'])[:24])))]),
            }),
            'sponsors':'\n'.join([replaces(templates['sponsors'],{
                'sponsor': s
            }) for s in sponsors])
        })
        print('weatherpage-保存输出文件')
        save_output_file(f'{locations[index]['id']}.xaml',output)
        save_output_file(f'{locations[index]['id']}.xaml.ini',BUILD_VERSION)

        if cwd['current']['temperature_2m'] > statisticsdata['now']['temp']['max'][0]:
            statisticsdata['now']['temp']['max'] = (cwd['current']['temperature_2m'], locations[index]['name'])
        if cwd['current']['temperature_2m'] < statisticsdata['now']['temp']['min'][0]:
            statisticsdata['now']['temp']['min'] = (cwd['current']['temperature_2m'], locations[index]['name'])
        if cwd['current']['wind_speed_10m'] > statisticsdata['now']['wind'][0]:
            statisticsdata['now']['wind'] = (cwd['current']['wind_speed_10m'], locations[index]['name'])
        if cwd['current']['weather_code'] not in statisticsdata['now']['weather']:
            statisticsdata['now']['weather'][cwd['current']['weather_code']] = 0
        statisticsdata['now']['weather'][cwd['current']['weather_code']] += 1
        
        for today_temp in (cwd['daily']['temperature_2m_max'][0], cwd['daily']['temperature_2m_min'][0]):
            if today_temp > statisticsdata['today']['temp']['max'][0]:
                statisticsdata['today']['temp']['max'] = (today_temp, locations[index]['name'])
            if today_temp < statisticsdata['today']['temp']['min'][0]:
                statisticsdata['today']['temp']['min'] = (today_temp, locations[index]['name'])
        if (cwd['daily']['temperature_2m_max'][0] - cwd['daily']['temperature_2m_min'][0]) > \
            (statisticsdata['today']['tempdiff'][0][0] - statisticsdata['today']['tempdiff'][0][1]):
            statisticsdata['today']['tempdiff'] = ((cwd['daily']['temperature_2m_max'][0], cwd['daily']['temperature_2m_min'][0]), locations[index]['name'])
        if cwd['daily']['wind_speed_10m_mean'][0] > statisticsdata['today']['wind'][0]:
            statisticsdata['today']['wind'] = (cwd['daily']['wind_speed_10m_mean'][0], locations[index]['name'])
        if cwd['daily']['weather_code'][0] not in statisticsdata['today']['weather']:
            statisticsdata['today']['weather'][cwd['daily']['weather_code'][0]] = 0
        statisticsdata['today']['weather'][cwd['daily']['weather_code'][0]] += 1

def statisticspage():
    global statisticsdata
    print(f'statisticspage-构建页面')
    now = datetime.now(timezone(timedelta(hours=8)))
    output = replaces(templates['statisticspage'],{
        'date': now.strftime("%m/%d"),
        'now_temp_max': str(statisticsdata['now']['temp']['max'][0])+'° '+statisticsdata['now']['temp']['max'][1],
        'now_temp_min': str(statisticsdata['now']['temp']['min'][0])+'° '+statisticsdata['now']['temp']['min'][1],
        'now_wind': str(statisticsdata['now']['wind'][0])+'km/h '+statisticsdata['now']['wind'][1],
        '': (
            now_weather_list := sorted(list(statisticsdata['now']['weather'].items()), key=lambda x: x[1], reverse=True),
            now_weather_list_item := lambda n: (wmocode_to_text(now_weather_list[n][0])+' '+str(now_weather_list[n][1])+'个地区') if len(now_weather_list) >= n+1 else ''
        ),
        'now_weather_1': now_weather_list_item(0),
        'now_weather_2': now_weather_list_item(1),
        'now_weather_3': now_weather_list_item(2),
        'now_weather_4': now_weather_list_item(3),
        'now_weather_5': now_weather_list_item(4),
        'today_temp_max': str(statisticsdata['today']['temp']['max'][0])+'° '+statisticsdata['today']['temp']['max'][1],
        'today_temp_min': str(statisticsdata['today']['temp']['min'][0])+'° '+statisticsdata['today']['temp']['min'][1],
        'today_tempdiff': str(statisticsdata['today']['tempdiff'][0][0]-statisticsdata['today']['tempdiff'][0][1])+'° '+statisticsdata['today']['tempdiff'][1],
        'today_wind': str(statisticsdata['today']['wind'][0])+'km/h '+statisticsdata['today']['wind'][1],
        '': (
            today_weather_list := sorted(list(statisticsdata['today']['weather'].items()), key=lambda x: x[1], reverse=True),
            today_weather_list_item := lambda n: (wmocode_to_text(today_weather_list[n][0])+' '+str(today_weather_list[n][1])+'个地区') if len(today_weather_list) >= n+1 else ''
        ),
        'today_weather_1': today_weather_list_item(0),
        'today_weather_2': today_weather_list_item(1),
        'today_weather_3': today_weather_list_item(2),
        'today_weather_4': today_weather_list_item(3),
        'today_weather_5': today_weather_list_item(4),
        'sponsors':'\n'.join([replaces(templates['sponsors'],{
            'sponsor': s
        }) for s in sponsors])
    })
    print('statisticspage-保存输出文件')
    save_output_file(f'statistics.xaml',output)
    save_output_file(f'statistics.xaml.ini',BUILD_VERSION)

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
    test_environment = os.path.exists(os.path.join(BASE_PATH,'test_environment'))
    if test_environment:
        sponsors = []
    else:
        sponsors = requests.get('https://v4.gh-proxy.org/https://github.com/wzyaeu/IfadianSponsorGet/raw/refs/heads/pagedata/output.json').json()


    load_all_template()

    print('init-运行choosepage')
    choosepage()

    print('init-运行weatherpage')
    weatherpage()

    print('init-statisticspage')
    statisticspage()

init()