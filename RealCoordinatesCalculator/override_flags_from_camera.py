"""
Override specific flags directly from camera
---------------------------------------------
Use this when the transformation formula produced wrong values for certain
flags (e.g. because the original old PTZ values for those flags were wrong).

Workflow:
  1. Position the camera at the correct location for each flag
     (using the camera's saved preset system).
  2. Press Enter — the script reads the live PTZ and updates that flag's
     entry in PTZCamValues_181_2026.txt in place.

CONFIGURATION — edit these:
"""

FLAGS_TO_OVERRIDE = [137]

NEW_CAMERA_INI = 'new_camera.ini'
PTZ_2026_FILE  = 'PTZCamValues_181_2026.txt'

# ─────────────────────────────────────────────────────────────────────────────

import re
import sys
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


def get_ptz(cam_ip, cam_port, user, password):
    """Return (pan, tilt, zoom) from the Dahua camera CGI."""
    url = f'http://{cam_ip}:{cam_port}/cgi-bin/ptz.cgi?action=getStatus'
    try:
        resp = requests.get(url, auth=HTTPDigestAuth(user, password), timeout=5)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise ConnectionError(f'Camera request failed: {e}')

    matches = re.findall(r'status\.Postion\[(\d+)\]=([\d.+-]+)', resp.text)
    if not matches:
        raise ValueError(f'No PTZ data in response:\n{resp.text}')

    positions = {int(m[0]): float(m[1]) for m in matches}
    return positions[0], positions[1], positions[2]


def load_ptz_file(filepath):
    """Load the 2026 file into an ordered list of (flag_num, line_string)."""
    entries = []
    with open(filepath, 'r') as fh:
        for line in fh:
            stripped = line.strip()
            if stripped and stripped.startswith('#'):
                head = stripped.split(' - ')[0]
                flag_num = int(head[1:])
                entries.append([flag_num, stripped])
            # skip blank lines at end
    return entries


def write_ptz_file(filepath, entries):
    with open(filepath, 'w') as fh:
        for _, line in entries:
            fh.write(line + '\n')


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':

    cam_ip, cam_port, user, password = load_config(NEW_CAMERA_INI)
    print(f'Camera: {cam_ip}:{cam_port}  (user={user})\n')

    # Quick connectivity test
    print('Testing camera connection...', end=' ', flush=True)
    try:
        pan, tilt, zoom = get_ptz(cam_ip, cam_port, user, password)
        print(f'OK  →  current PTZ = pan={pan:.2f}, tilt={tilt:.2f}, zoom={zoom:.2f}\n')
    except Exception as e:
        print(f'FAILED\n{e}')
        print('Check new_camera.ini and try again.')
        sys.exit(1)

    # Load the current 2026 file
    entries = load_ptz_file(PTZ_2026_FILE)
    flag_index = {flag_num: i for i, (flag_num, _) in enumerate(entries)}

    print(f'Will process {len(FLAGS_TO_OVERRIDE)} flags: {FLAGS_TO_OVERRIDE}')
    print(f'Editing file: {PTZ_2026_FILE}\n')

    for flag_num in FLAGS_TO_OVERRIDE:
        is_new = flag_num not in flag_index

        print(f'─── Flag #{flag_num} {"(NEW — will be appended)" if is_new else "───────────────────────────────"}')
        if not is_new:
            print(f'    Current value in file: {entries[flag_index[flag_num]][1]}')
        print(f'    Position the camera at the correct preset for flag #{flag_num}, then press Enter.')
        print(f'    (type "s" + Enter to skip, "q" + Enter to quit)')

        user_input = input('    > ').strip().lower()
        if user_input == 'q':
            print('Quit.')
            break
        if user_input == 's':
            print(f'    Skipped flag #{flag_num}.')
            continue

        try:
            new_pan, new_tilt, new_zoom = get_ptz(cam_ip, cam_port, user, password)
        except Exception as e:
            print(f'    ERROR reading camera: {e}')
            retry = input('    Retry? (y/n): ').strip().lower()
            if retry == 'y':
                try:
                    new_pan, new_tilt, new_zoom = get_ptz(cam_ip, cam_port, user, password)
                except Exception as e2:
                    print(f'    Failed again: {e2}. Skipping.')
                    continue
            else:
                continue

        new_line = f'#{flag_num} - {new_pan:.2f} , {new_tilt:.2f}, {new_zoom:.2f}'

        if is_new:
            entries.append([flag_num, new_line])
            flag_index[flag_num] = len(entries) - 1
            print(f'    Appended: {new_line}\n')
        else:
            entries[flag_index[flag_num]][1] = new_line
            print(f'    Updated:  {new_line}\n')

        # Save after every flag so progress is never lost
        write_ptz_file(PTZ_2026_FILE, entries)

    print(f'Done. {PTZ_2026_FILE} has been updated.')
