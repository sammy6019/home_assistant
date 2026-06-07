import requests
import os
import subprocess
import fcntl
from datetime import datetime

LOCK_FILE = '/tmp/flood_monitor.lock'

HA_TOKEN = os.environ.get('HA_TOKEN')
if not HA_TOKEN:
    try:
        with open('/mnt/ssd/flood-monitor/.env') as f:
            for line in f:
                if line.startswith('HA_TOKEN='):
                    HA_TOKEN = line.strip().split('=', 1)[1]
    except Exception as e:
        print(f'Warning: Failed to load .env: {e}')

HA_URL = 'http://192.168.1.227:8123'

def is_nighttime():
    """True between 10pm and 6am Central time"""
    hour = int(datetime.now().strftime('%H'))
    return hour >= 22 or hour < 6

def is_raining():
    """Check if it's currently raining via Home Assistant weather"""
    try:
        with requests.get(
            f'{HA_URL}/api/states/weather.forecast_home',
            headers={'Authorization': f'Bearer {HA_TOKEN}'},
            timeout=15
        ) as response:
            response.raise_for_status()
            weather = response.json()
        condition = weather['state'].lower()
        humidity = weather['attributes'].get('humidity', 0)
        temperature = weather['attributes'].get('temperature', 0)
        print(f'Current condition: {condition}, Humidity: {humidity}%, Temp: {temperature}F')

        rain_conditions = ['rainy', 'pouring', 'lightning', 'lightning-rainy',
                          'hail', 'snowy-rainy']

        is_rain_condition = any(r in condition for r in rain_conditions)

        # Stricter humidity threshold at night to reduce false positives
        if is_nighttime():
            is_humid_enough = humidity >= 88
            print(f'Nighttime mode — humidity threshold: 88% (current: {humidity}%)')
        else:
            is_humid_enough = humidity >= 75
            print(f'Daytime mode — humidity threshold: 75% (current: {humidity}%)')

        return is_rain_condition and is_humid_enough

    except Exception as e:
        print(f'Error checking weather: {e}')
        return False

if __name__ == '__main__':
    night = is_nighttime()
    print(f'Time: {datetime.now().strftime("%H:%M")} | Nighttime mode: {night}')

    if is_raining():
        print('RAINING - running flood monitor')
        try:
            lock = open(LOCK_FILE, 'w')
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('flood_monitor already running, skipping')
        else:
            try:
                subprocess.run(['python3', '/mnt/ssd/flood-monitor/flood_monitor.py'], timeout=300)
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)
                lock.close()
    else:
        print('NOT raining - skipping')
