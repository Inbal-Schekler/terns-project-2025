"""
Set exact tour schedule times on the Dahua PTZ camera.
-------------------------------------------------------
Edit SCHEDULE below, then run the script.

SCHEDULE maps tour index (0, 1, 2, ...) to a list of (start, end) strings.
  - Up to 6 time slots per tour (indices 0–5).
  - Times in "HH:MM:SS" format.
  - All 7 days (Sun–Sat) get the same schedule.
  - Slots not listed are disabled.

Current tours on camera (as of April 2026):
  Tour [0][0]  TourId=1  (south sweep group 1)
  Tour [0][1]  TourId=2  (south sweep group 2)
"""

# ── EDIT THIS ─────────────────────────────────────────────────────────────────

NEW_CAMERA_INI = 'new_camera.ini'

# tour_index → list of (start_time, end_time) strings
#
# Scan 1 starts at 10:01:50, Scan 2 starts at 15:01:50.
# Each scan = Tour[0][0] (32 flags × 15s = 8min) then Tour[0][1] (15 flags × 15s = 3min45s).
# 10-second gap between Tour[0][0] end and Tour[0][1] start.
SCHEDULE = {
    0: [                                # Tour [0][0] — TourId=1  (32 flags × 15s = 8:00)
        ('10:01:50', '10:09:50'),       # morning scan
        ('15:01:50', '15:09:50'),       # afternoon scan
    ],
    1: [                                # Tour [0][1] — TourId=2  (15 flags × 15s = 3:45)
        ('10:10:00', '10:13:45'),       # morning scan  (10s gap after Tour[0][0])
        ('15:10:00', '15:13:45'),       # afternoon scan
    ],
}

DRY_RUN = False  # True = print only, don't apply; False = apply to camera

# ─────────────────────────────────────────────────────────────────────────────

import configparser
import requests
from requests.auth import HTTPDigestAuth


def load_config(ini_path):
    cfg = configparser.ConfigParser()
    cfg.read(ini_path)
    return (cfg.get('General', 'CAM_IP'),
            cfg.get('General', 'CAM_PORT'),
            cfg.get('General', 'USER_NAME'),
            cfg.get('General', 'PASSWORD'))


DISABLED_SLOT = '0 00:00:00-23:59:59'
NUM_DAYS  = 7   # indices 0–6
NUM_SLOTS = 6   # indices 0–5


def build_params(schedule):
    """Build query-string key=value pairs for setConfig."""
    params = {}
    for tour_idx, slots in schedule.items():
        for day in range(NUM_DAYS):
            for slot in range(NUM_SLOTS):
                key = f'table.PtzAutoMovement[0][{tour_idx}].TimeSection[{day}][{slot}]'
                if slot < len(slots):
                    start, end = slots[slot]
                    params[key] = f'1 {start}-{end}'
                else:
                    params[key] = DISABLED_SLOT
    return params


def get_current_schedule(base, auth):
    """Read and display the current PtzAutoMovement schedule."""
    url = f'{base}/configManager.cgi?action=getConfig&name=PtzAutoMovement'
    r = requests.get(url, auth=auth, timeout=5)
    lines = [l for l in r.text.splitlines() if 'TimeSection' in l]
    return lines


if __name__ == '__main__':
    cam_ip, cam_port, user, password = load_config(NEW_CAMERA_INI)
    auth = HTTPDigestAuth(user, password)
    base = f'http://{cam_ip}:{cam_port}/cgi-bin'

    print(f'Camera: {cam_ip}:{cam_port}\n')

    # Show current schedule
    print('Current schedule (TimeSection lines only):')
    for line in get_current_schedule(base, auth):
        print(' ', line)

    # Build new params
    params = build_params(SCHEDULE)

    print(f'\nNew schedule to apply ({len(params)} params):')
    # Print unique slots (day 0 only, to avoid repetition)
    for key, val in params.items():
        if '[0][' in key.split('TimeSection')[1]:   # only day 0
            print(f'  {key} = {val}')

    if DRY_RUN:
        print('\n[DRY RUN] Set DRY_RUN = False to actually apply.')
    else:
        print('\nApplying...')
        url = f'{base}/configManager.cgi?action=setConfig'
        r = requests.get(url, params=params, auth=auth, timeout=10)
        print(f'Response: {r.status_code}  {r.text.strip()}')

        # Verify
        print('\nVerifying (new TimeSection lines):')
        for line in get_current_schedule(base, auth):
            print(' ', line)
