"""
Fix south camera timezone / clock to Israel time (UTC+3 in summer, UTC+2 in winter).

The camera had NTP disabled and was showing time 1 hour behind Israel time.

This script:
  1. Enables NTP (so the camera auto-syncs and handles DST transitions).
  2. Immediately sets the clock to the correct Israel time right now
     (so you don't have to wait for the next NTP sync).

Run it, then verify the camera clock in the UI shows the correct time.
"""

import configparser
import datetime
import requests
from requests.auth import HTTPDigestAuth

NEW_CAMERA_INI = 'new_camera.ini'

# ─────────────────────────────────────────────────────────────────────────────

def load_config(ini_path):
    cfg = configparser.ConfigParser()
    cfg.read(ini_path)
    return (cfg.get('General', 'CAM_IP'),
            cfg.get('General', 'CAM_PORT'),
            cfg.get('General', 'USER_NAME'),
            cfg.get('General', 'PASSWORD'))


def get_camera_time(base, auth):
    r = requests.get(f'{base}/global.cgi?action=getCurrentTime', auth=auth, timeout=5)
    # response: "result=2026-04-10 10:18:24\n"
    return r.text.strip().replace('result=', '')


def set_camera_time(base, auth, dt_str):
    """dt_str format: 'YYYY-MM-DD HH:MM:SS'"""
    url = f'{base}/global.cgi?action=setCurrentTime'
    r = requests.get(url, params={'time': dt_str}, auth=auth, timeout=5)
    return r.text.strip()


def enable_ntp(base, auth):
    url = f'{base}/configManager.cgi?action=setConfig'
    params = {'table.NTP.Enable': 'true'}
    r = requests.get(url, params=params, auth=auth, timeout=5)
    return r.text.strip()


if __name__ == '__main__':
    cam_ip, cam_port, user, password = load_config(NEW_CAMERA_INI)
    auth = HTTPDigestAuth(user, password)
    base = f'http://{cam_ip}:{cam_port}/cgi-bin'

    print(f'Camera: {cam_ip}:{cam_port}\n')

    # Step 1: Show current camera time
    cam_time = get_camera_time(base, auth)
    print(f'Current camera time : {cam_time}')

    # Step 2: Enable NTP (Jerusalem timezone already set — handles DST automatically)
    print('Enabling NTP...', end=' ')
    resp = enable_ntp(base, auth)
    print(f'Response: {resp}')

    # Step 3: Manually set clock to correct Israel time right now
    # datetime.datetime.now() is your local PC time — make sure your PC is on Israel time,
    # or replace with the exact Israel time string, e.g. '2026-04-10 11:20:00'
    israel_now = datetime.datetime.now()  # assumes your PC clock is on Israel time
    israel_str = israel_now.strftime('%Y-%m-%d %H:%M:%S')
    print(f'\nSetting camera clock to: {israel_str}  (from your PC clock)')
    resp2 = set_camera_time(base, auth, israel_str)
    print(f'Response: {resp2}')

    # Step 4: Verify
    import time
    time.sleep(1)
    new_cam_time = get_camera_time(base, auth)
    print(f'\nCamera time after fix: {new_cam_time}')
    print('Done. The camera clock should now match Israel time.')
    print('NTP is enabled — it will stay in sync and handle summer/winter transitions automatically.')
