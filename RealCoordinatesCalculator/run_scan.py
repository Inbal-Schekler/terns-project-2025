"""
External scan controller for south PTZ camera (camera 181).
-----------------------------------------------------------
Runs both tour groups sequentially at exact timing using ONVIF GotoPreset.

Usage:
  python run_scan.py          -- runs the full scan (Tour1 then Tour2) once right now
  python run_scan.py --dry    -- print the preset sequence without moving the camera

Set up via Windows Task Scheduler to trigger at 10:01:50 and 15:01:50 every day.
Before using: disable the camera's internal schedule in the camera web UI,
so this script is the only thing controlling the scan.

CONFIGURATION — edit these:
"""

# Preset order for each tour.
# Tour 1: 32 flags
TOUR1_PRESETS = [
    92, 93, 94, 95, 96, 97, 98, 99, 100, 101,
    102, 103, 104, 105, 106, 107, 108, 109, 110, 111,
    112, 113, 114, 115, 116, 117, 118, 119,
    121, 122, 137, 123,
]

# Tour 2: 15 flags
TOUR2_PRESETS = [
    124, 125, 126, 127, 128, 129, 130,
    131, 132, 133, 135, 136, 138, 134,
    1,
]

DWELL_SECONDS = 15        # how long to stay at each preset
GAP_SECONDS   = 10        # pause between Tour1 end and Tour2 start

NEW_CAMERA_INI = 'new_camera.ini'
ONVIF_PROFILE  = 'MediaProfile00000'

# ─────────────────────────────────────────────────────────────────────────────

import sys
import time
import configparser
import hashlib
import base64
import datetime
import os
import re
import requests


def load_config(ini_path):
    cfg = configparser.ConfigParser()
    cfg.read(ini_path)
    return (cfg.get('General', 'CAM_IP'),
            cfg.get('General', 'CAM_PORT'),
            cfg.get('General', 'USER_NAME'),
            cfg.get('General', 'PASSWORD'))


def onvif_request(service_url, action_body, user, password):
    nonce_raw = os.urandom(16)
    nonce_b64 = base64.b64encode(nonce_raw).decode()
    created = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    digest = base64.b64encode(
        hashlib.sha1(nonce_raw + created.encode() + password.encode()).digest()
    ).decode()
    envelope = f'''<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <s:Header>
    <Security xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
      <UsernameToken>
        <Username>{user}</Username>
        <Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{digest}</Password>
        <Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{nonce_b64}</Nonce>
        <Created xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">{created}</Created>
      </UsernameToken>
    </Security>
  </s:Header>
  <s:Body>{action_body}</s:Body>
</s:Envelope>'''
    return requests.post(service_url, data=envelope, timeout=10,
                         headers={'Content-Type': 'application/soap+xml'})


def goto_preset(ptz_url, profile, preset_token, user, password):
    body = f'''<tptz:GotoPreset xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl">
  <tptz:ProfileToken>{profile}</tptz:ProfileToken>
  <tptz:PresetToken>{preset_token}</tptz:PresetToken>
</tptz:GotoPreset>'''
    r = onvif_request(ptz_url, body, user, password)
    return r.status_code == 200


def run_tour(ptz_url, profile, presets, dwell, user, password, dry_run=False):
    for i, preset in enumerate(presets):
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        print(f'  [{ts}] preset {preset} ({i+1}/{len(presets)})', flush=True)
        if not dry_run:
            ok = goto_preset(ptz_url, profile, str(preset), user, password)
            if not ok:
                print(f'  WARNING: GotoPreset {preset} failed')
            time.sleep(dwell)


def run_full_scan(dry_run=False):
    cam_ip, cam_port, user, password = load_config(NEW_CAMERA_INI)
    ptz_url = f'http://{cam_ip}:{cam_port}/onvif/ptz_service'

    start_ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'=== Scan started at {start_ts} ===')
    if dry_run:
        print('[DRY RUN — camera will not move]\n')

    print(f'Tour 1: {len(TOUR1_PRESETS)} presets x {DWELL_SECONDS}s each')
    run_tour(ptz_url, ONVIF_PROFILE, TOUR1_PRESETS, DWELL_SECONDS, user, password, dry_run)

    print(f'\nGap: {GAP_SECONDS}s between tours')
    if not dry_run:
        time.sleep(GAP_SECONDS)

    print(f'\nTour 2: {len(TOUR2_PRESETS)} presets x {DWELL_SECONDS}s each')
    run_tour(ptz_url, ONVIF_PROFILE, TOUR2_PRESETS, DWELL_SECONDS, user, password, dry_run)

    end_ts = datetime.datetime.now().strftime('%H:%M:%S')
    total = (len(TOUR1_PRESETS) + len(TOUR2_PRESETS)) * DWELL_SECONDS + GAP_SECONDS
    print(f'\n=== Scan finished at {end_ts} (expected duration: {total//60}m {total%60}s) ===')


TARGET_SECOND = 50  # start scan at HH:MM:50 (Task Scheduler triggers at HH:MM:00)


if __name__ == '__main__':
    dry_run = '--dry' in sys.argv

    if not dry_run:
        # Wait until the :50 second mark of the current minute
        now = datetime.datetime.now()
        wait = TARGET_SECOND - now.second
        if wait < 0:
            wait += 60   # already past :50, wait to next minute's :50
        if wait > 0:
            print(f'Waiting {wait}s until :{TARGET_SECOND:02d}...', flush=True)
            time.sleep(wait)

    run_full_scan(dry_run=dry_run)
