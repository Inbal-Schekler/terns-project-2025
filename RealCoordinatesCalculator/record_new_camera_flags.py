"""
Step 1 of New Camera Calibration
---------------------------------
Point the new camera at each known flag and press Enter.
The script reads the live PTZ from the camera and records it
alongside the original PTZ values for that flag.

Output file (PTZCamValues_181_new_raw.txt) will have columns:
    flag_num  old_pan  old_tilt  old_zoom  new_pan  new_tilt  new_zoom

Just run:
    python record_new_camera_flags.py
"""

import re
import sys
import configparser
import requests
from requests.auth import HTTPDigestAuth

# ── CONFIGURATION ─────────────────────────────────────────────────────────────

# Flags you want to calibrate. Add or remove numbers here.
FLAGS_TO_RECORD = [92, 96, 106, 134]

# Set to True to re-record flags that were already saved (overwrites old data).
# Set to False to skip flags that are already in the output file.
OVERWRITE = True

# File paths (you normally don't need to change these)
NEW_CAMERA_INI   = 'new_camera.ini'
OLD_PTZ_FILE     = 'PTZCamValues_181.txt'
OUTPUT_FILE      = 'PTZCamValues_181_new_raw.txt'

# ─────────────────────────────────────────────────────────────────────────────


# ── camera ────────────────────────────────────────────────────────────────────

def load_config(ini_path: str):
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

    # Response contains lines like: status.Postion[0]=305.760000
    matches = re.findall(r'status\.Postion\[(\d+)\]=([\d.+-]+)', resp.text)
    if not matches:
        raise ValueError(f'No PTZ data in response:\n{resp.text}')

    positions = {int(m[0]): float(m[1]) for m in matches}
    # Dahua: [0]=Pan, [1]=Tilt, [2]=Zoom
    return positions[0], positions[1], positions[2]


# ── old PTZ file ──────────────────────────────────────────────────────────────

def load_old_ptz(filepath: str) -> dict:
    """
    Parse PTZCamValues_181.txt.
    Format per line: #flag_num - pan , tilt, zoom
    Returns {flag_num: (pan, tilt, zoom)}
    """
    old = {}
    with open(filepath, 'r') as fh:
        for line in fh:
            line = line.strip()
            if not line or not line.startswith('#'):
                continue
            # split on ' - '
            head, rest = line.split(' - ', 1)
            flag_num = int(head[1:])
            parts = [v.strip() for v in rest.split(',')]
            pan  = float(parts[0])
            tilt = float(parts[1])
            zoom = float(parts[2])
            old[flag_num] = (pan, tilt, zoom)
    return old


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':

    # Load old values
    old_ptz = load_old_ptz(OLD_PTZ_FILE)
    print(f'Loaded {len(old_ptz)} flags from {OLD_PTZ_FILE}')

    # Camera connection
    cam_ip, cam_port, user, password = load_config(NEW_CAMERA_INI)
    print(f'Camera: {cam_ip}:{cam_port}  (user={user})\n')

    # Quick connectivity test
    print('Testing camera connection...', end=' ', flush=True)
    try:
        pan, tilt, zoom = get_ptz(cam_ip, cam_port, user, password)
        print(f'OK  →  current PTZ = pan={pan:.2f}, tilt={tilt:.2f}, zoom={zoom:.2f}\n')
    except Exception as e:
        print(f'FAILED\n{e}')
        print('Check new_camera.ini (IP, port, password) and try again.')
        sys.exit(1)

    overwrite_mode = OVERWRITE
    if overwrite_mode:
        print(f'OVERWRITE=True → will re-record all flags (old data will be replaced)\n')
    print(f'Will record {len(FLAGS_TO_RECORD)} flags: {FLAGS_TO_RECORD}\n')

    # When overwriting, start fresh; otherwise load what's already saved
    already_written = set()
    if not overwrite_mode:
        try:
            with open(OUTPUT_FILE, 'r') as existing:
                for line in existing:
                    parts = line.strip().split('\t')
                    if parts and parts[0].isdigit():
                        already_written.add(int(parts[0]))
        except FileNotFoundError:
            pass  # file doesn't exist yet — that's fine

    # 'w' clears the file when overwriting; 'a' appends when not
    open_mode = 'w' if overwrite_mode else 'a'
    with open(OUTPUT_FILE, open_mode) as out:
        # Always write header when opening fresh
        if overwrite_mode or not already_written:
            out.write('flag_num\told_pan\told_tilt\told_zoom\tnew_pan\tnew_tilt\tnew_zoom\n')

        for flag_num in FLAGS_TO_RECORD:
            if flag_num not in old_ptz:
                print(f'  [skip] Flag {flag_num} not found in {OLD_PTZ_FILE}.')
                continue
            if flag_num in already_written:
                print(f'  [skip] Flag {flag_num} already recorded in {OUTPUT_FILE}.')
                continue

            old_pan, old_tilt, old_zoom = old_ptz[flag_num]

            print(f'─── Flag #{flag_num} ───────────────────────────────')
            print(f'    Old camera: pan={old_pan:.2f}  tilt={old_tilt:.2f}  zoom={old_zoom:.1f}')
            print(f'    Point the NEW camera at flag #{flag_num}, then press Enter.')
            print(f'    (type "s" + Enter to skip this flag, "q" + Enter to quit)')

            user_input = input('    > ').strip().lower()
            if user_input == 'q':
                print('Quit.')
                break
            if user_input == 's':
                print(f'    Skipped flag #{flag_num}.')
                continue

            # Read current PTZ from new camera
            try:
                new_pan, new_tilt, new_zoom = get_ptz(cam_ip, cam_port, user, password)
            except Exception as e:
                print(f'    ERROR reading camera: {e}')
                retry = input('    Retry? (y/n): ').strip().lower()
                if retry == 'y':
                    try:
                        new_pan, new_tilt, new_zoom = get_ptz(cam_ip, cam_port, user, password)
                    except Exception as e2:
                        print(f'    Failed again: {e2}. Skipping flag #{flag_num}.')
                        continue
                else:
                    continue

            print(f'    New camera: pan={new_pan:.4f}  tilt={new_tilt:.4f}  zoom={new_zoom:.4f}')
            print(f'    Δpan={new_pan - old_pan:+.4f}  '
                  f'Δtilt={new_tilt - old_tilt:+.4f}  '
                  f'zoom_ratio={new_zoom / old_zoom:.4f}\n')

            out.write(f'{flag_num}\t{old_pan}\t{old_tilt}\t{old_zoom}'
                      f'\t{new_pan:.4f}\t{new_tilt:.4f}\t{new_zoom:.4f}\n')
            out.flush()
            already_written.add(flag_num)

    print(f'\nDone. Saved to: {OUTPUT_FILE}')
    print(f'Total flags recorded so far: {len(already_written)}')
    print('\nNext step: once all 3 flags are recorded, run compute_ptz_transform.py')
