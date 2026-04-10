"""
Step 2 of New Camera Calibration  –  compute_ptz_transform.py
==============================================================

PURPOSE
-------
Camera 181 was replaced with a new (upgraded) model in 2026.
This script derives the PTZ transformation from old camera → new camera
using 3 manually calibrated reference flags, then applies it to all 48
flags to produce PTZCamValues_181_2026.txt.


HOW THE TRANSFORMATION WAS DERIVED
------------------------------------
We manually pointed the new camera at 3 known flags (92, 96, 106) and
recorded the new camera's raw PTZ values alongside the original ones.
Results (from record_new_camera_flags.py):

    Flag |  old_pan  new_pan   Δpan  | old_tilt  new_tilt  Δtilt | old_zoom  new_zoom  ratio
    -----+---------------------------------+-------------------------------+------------------------
     92  |  305.76   294.07  -11.69  |   6.14     6.49   +0.35  |  45.6     60.30   1.3224
     96  |  277.20   264.26  -12.94  |   7.09     7.58   +0.49  |  50.8     67.41   1.3270
    106  |  297.86   285.73  -12.13  |  11.11    12.55   +1.44  |  34.0     48.07   1.4139


PAN – constant offset
    The pan deltas are very consistent (-11.69, -12.94, -12.13).
    This means the new camera is physically rotated by ~12° relative to
    the old one on its mount (same mechanism, just different orientation).
    We use the mean offset:  new_pan = old_pan + Δpan_mean

TILT – linear model (not just an offset)
    The tilt delta grows with tilt value (+0.35, +0.49, +1.44).
    A constant offset would fail badly here.
    Physical reason: the new camera's tilt mechanism has a different
    angular scale – 1 raw unit on the new camera corresponds to a
    different real angle than 1 unit on the old camera.
    We fit:  new_tilt = a_tilt × old_tilt + b_tilt  (least-squares over 3 points)

    Fit quality check:
        Flag 92:   predicted 6.45  vs actual 6.49  → error 0.04°
        Flag 96:   predicted 7.62  vs actual 7.58  → error 0.04°
        Flag 106:  predicted 12.56 vs actual 12.55 → error 0.01°
    For comparison, a constant-offset model gives errors of 0.27–0.68°.
    The linear model is ~10× more accurate.

ZOOM – linear model (scale also changed)
    The zoom ratio also grows (1.32, 1.33, 1.41), so same reasoning applies.
    We fit:  new_zoom = a_zoom × old_zoom + b_zoom  (least-squares over 3 points)

NOTE – mod file (focal length f) is NOT updated here.
    The algorithm mod file (PTZCamValues181_mod.txt) uses pitch, yaw, and f
    (focal length in pixels).  pitch and yaw are physical world angles —
    they don't change because the camera is in the same location looking at
    the same island.  Only f needs updating (new zoom scale → new formula).
    That is handled separately in Step 3.


INPUTS
------
    PTZCamValues_181.txt          – original 48-flag raw PTZ values
    PTZCamValues_181_new_raw.txt  – 3-flag calibration data (from Step 1)

OUTPUT
------
    PTZCamValues_181_2026.txt     – new raw PTZ values for all 48 flags
                                    (same format as the original file)
"""

import numpy as np


# ── file paths ────────────────────────────────────────────────────────────────

OLD_PTZ_FILE      = 'PTZCamValues_181.txt'
CALIBRATION_FILE  = 'PTZCamValues_181_new_raw.txt'
OUTPUT_FILE       = 'PTZCamValues_181_2026.txt'


# ── helpers ───────────────────────────────────────────────────────────────────

def load_old_ptz(filepath):
    """
    Parse PTZCamValues_181.txt.
    Returns list of (flag_num, pan, tilt, zoom) in original file order.
    """
    flags = []
    with open(filepath, 'r') as fh:
        for line in fh:
            line = line.strip()
            if not line or not line.startswith('#'):
                continue
            head, rest = line.split(' - ', 1)
            flag_num = int(head[1:])
            parts = [v.strip() for v in rest.split(',')]
            flags.append((flag_num, float(parts[0]), float(parts[1]), float(parts[2])))
    return flags


def load_calibration(filepath):
    """
    Parse PTZCamValues_181_new_raw.txt (tab-separated, has header row).
    Returns list of (flag_num, old_pan, old_tilt, old_zoom, new_pan, new_tilt, new_zoom).
    """
    rows = []
    with open(filepath, 'r') as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith('flag_num'):
                continue
            parts = line.split('\t')
            rows.append((
                int(parts[0]),
                float(parts[1]), float(parts[2]), float(parts[3]),
                float(parts[4]), float(parts[5]), float(parts[6]),
            ))
    return rows


def fit_linear(old_vals, new_vals):
    """Least-squares fit: new = a * old + b.  Returns (a, b)."""
    old = np.array(old_vals)
    new = np.array(new_vals)
    A = np.column_stack([old, np.ones(len(old))])
    result, _, _, _ = np.linalg.lstsq(A, new, rcond=None)
    return result[0], result[1]


def fit_constant_offset(old_vals, new_vals):
    """Mean offset: new = old + b."""
    deltas = [n - o for o, n in zip(old_vals, new_vals)]
    return np.mean(deltas)


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':

    # 1. Load data
    old_flags = load_old_ptz(OLD_PTZ_FILE)
    cal = load_calibration(CALIBRATION_FILE)
    print(f'Loaded {len(old_flags)} flags from {OLD_PTZ_FILE}')
    print(f'Loaded {len(cal)} calibration points from {CALIBRATION_FILE}\n')

    old_pans  = [r[1] for r in cal]
    old_tilts = [r[2] for r in cal]
    old_zooms = [r[3] for r in cal]
    new_pans  = [r[4] for r in cal]
    new_tilts = [r[5] for r in cal]
    new_zooms = [r[6] for r in cal]

    # 2. Fit transformation models
    pan_offset          = fit_constant_offset(old_pans,  new_pans)
    a_tilt, b_tilt      = fit_linear(old_tilts, new_tilts)
    a_zoom, b_zoom      = fit_linear(old_zooms, new_zooms)

    print('═══ Fitted transformation formulas ════════════════════════════')
    print(f'  pan  (constant offset):  new_pan  = old_pan  + ({pan_offset:+.4f})')
    print(f'  tilt (linear):           new_tilt = {a_tilt:.4f} × old_tilt + ({b_tilt:+.4f})')
    print(f'  zoom (linear):           new_zoom = {a_zoom:.4f} × old_zoom + ({b_zoom:+.4f})')
    print()

    # 3. Verify fit against calibration points
    print('═══ Fit verification (calibration flags) ══════════════════════')
    print(f'  {"flag":>4}  {"pan_pred":>9} {"pan_act":>9} {"Δpan":>7}  '
          f'{"tilt_pred":>10} {"tilt_act":>9} {"Δtilt":>7}  '
          f'{"zoom_pred":>10} {"zoom_act":>9} {"Δzoom":>7}')
    for flag_num, op, ot, oz, np_, nt, nz in cal:
        pp = op + pan_offset
        tp = a_tilt * ot + b_tilt
        zp = a_zoom * oz + b_zoom
        print(f'  {flag_num:>4}  {pp:9.4f} {np_:9.4f} {pp-np_:+7.4f}  '
              f'{tp:10.4f} {nt:9.4f} {tp-nt:+7.4f}  '
              f'{zp:10.4f} {nz:9.4f} {zp-nz:+7.4f}')
    print()

    # 4. Apply transformation to all 48 flags
    print('═══ Applying to all flags ══════════════════════════════════════')
    with open(OUTPUT_FILE, 'w') as out:
        for flag_num, old_pan, old_tilt, old_zoom in old_flags:
            new_pan  = old_pan  + pan_offset
            new_tilt = a_tilt * old_tilt + b_tilt
            new_zoom = a_zoom * old_zoom + b_zoom
            line = f'#{flag_num} - {new_pan:.2f} , {new_tilt:.2f}, {new_zoom:.2f}\n'
            out.write(line)
            marker = ' ← calibration flag' if flag_num in {r[0] for r in cal} else ''
            print(f'  flag {flag_num:>3}: '
                  f'pan {old_pan:.2f} → {new_pan:.2f}  '
                  f'tilt {old_tilt:.2f} → {new_tilt:.2f}  '
                  f'zoom {old_zoom:.1f} → {new_zoom:.2f}'
                  f'{marker}')

    print(f'\nDone. New PTZ values written to: {OUTPUT_FILE}')
    print('Inspect the file, then proceed to Step 3 (update focal length f in mod file).')
