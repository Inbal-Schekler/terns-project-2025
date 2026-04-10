"""
Explore Dahua camera schedule/tour configuration via HTTP API.
Run this to see how the camera stores its tour schedule,
so we can set exact times programmatically.
"""

import configparser
import requests
from requests.auth import HTTPDigestAuth

# ── config ────────────────────────────────────────────────────────────────────
config = configparser.ConfigParser()
config.read('new_camera.ini')
CAM_IP   = config.get('General', 'CAM_IP')
CAM_PORT = config.get('General', 'CAM_PORT')
USER     = config.get('General', 'USER_NAME')
PASS     = config.get('General', 'PASSWORD')

auth = HTTPDigestAuth(USER, PASS)
base = f'http://{CAM_IP}:{CAM_PORT}/cgi-bin'

def get_config(name):
    url = f'{base}/configManager.cgi?action=getConfig&name={name}'
    r = requests.get(url, auth=auth, timeout=5)
    return r.text

# ── fetch relevant config sections ────────────────────────────────────────────
import json

# 1. Try configManager with many section names
sections = [
    'Patrol', 'PatrolTask', 'GroupTour', 'PtzGroupTask',
    'PtzTask', 'PtzPatrol', 'NormalSchedule', 'RecordSchedule',
    'ActionRule', 'EventHandler', 'TimingTask', 'TimePlan',
    'TrackPlan', 'CruiseTask', 'PresetTask', 'PresetScan',
    'VideoInMode', 'VideoInOptions', 'CommSchedule',
]

print('=== configManager.cgi results ===')
for section in sections:
    result = get_config(section)
    if 'Error' in result or 'Unknown' in result or result.strip() == '':
        continue
    print(f'\n{"="*60}\n  Config: {section}\n{"="*60}')
    print(result[:2000])

def safe_print(text, limit=3000):
    """Print text safely, replacing unencodable characters."""
    print(text[:limit].encode('ascii', errors='replace').decode('ascii'))

# 2. Try ptz.cgi with tour/patrol actions
print('\n\n=== ptz.cgi actions ===')
ptz_actions = [
    'getTour', 'getGroupTour', 'getPatrol', 'getCruise',
    'getPresets', 'getConfig', 'getStatus',
]
for action in ptz_actions:
    url = f'{base}/ptz.cgi?action={action}&channel=0'
    r = requests.get(url, auth=auth, timeout=5)
    if r.text.strip() and 'Error' not in r.text and 'Unknown' not in r.text:
        print(f'\n--- ptz.cgi?action={action} ---')
        safe_print(r.text)

# 3. Try JSON-RPC2 API (newer Dahua firmware)
print('\n\n=== JSON-RPC2 API ===')
rpc_url = f'http://{CAM_IP}:{CAM_PORT}/RPC2'
for name in ['Tour', 'GroupTour', 'PtzTask', 'TimedTask', 'Patrol']:
    payload = {"method": "configManager.getConfig", "params": {"name": name}, "id": 1}
    try:
        r = requests.post(rpc_url, json=payload, auth=auth, timeout=5)
        if '"result":true' in r.text or ('"params"' in r.text and 'null' not in r.text):
            print(f'\n--- RPC2 {name} ---')
            safe_print(r.text)
    except Exception as e:
        print(f'RPC2 error: {e}')
        break

# 4. Try configManager with no name (may list available sections or error with hint)
print('\n\n=== configManager - no name ===')
url = f'{base}/configManager.cgi?action=getConfig'
r = requests.get(url, auth=auth, timeout=5)
safe_print(r.text)

# 5. Try PTZ schedule via mediaFileFinder or specific task CGIs
print('\n\n=== other CGI endpoints ===')
other_urls = [
    f'{base}/ptz.cgi?action=getGroupTourInfo&channel=0',
    f'{base}/configManager.cgi?action=getConfig&name=CommSchedule',
    f'{base}/configManager.cgi?action=getConfig&name=PtzPresetTour',
    f'{base}/configManager.cgi?action=getConfig&name=PtzAutoMovement',
]
for url in other_urls:
    r = requests.get(url, auth=auth, timeout=5)
    if r.text.strip() and 'Error' not in r.text and 'Unknown' not in r.text:
        print(f'\n--- {url.split("?")[1]} ---')
        safe_print(r.text)
