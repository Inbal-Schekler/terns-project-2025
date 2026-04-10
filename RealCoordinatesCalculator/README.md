# RealCoordinatesCalculator

This module calculates the real-world (drone-image) coordinates of objects detected in PTZ camera footage. Each flag position (camera preset) is mapped from camera pixel space to physical coordinates on the colony drone image, using the camera's pan/tilt/zoom values and a calibration model.

There are two cameras covering the colony:
- **Camera 181** — South camera
- **Camera 191** — North camera

---

## 2026 Update: South Camera (181) Replacement

In 2026, Camera 181 was replaced with a new upgraded model. The new camera has:
- A **different zoom scale** (stronger zoom at the same zoom value)
- A **slightly different mounting orientation** (~12° pan offset, different tilt scale)

This required full recalibration of all 47 flag presets for the south camera. The sections below describe everything that was done and the scripts used.

---

## Calibration Workflow (South Camera 2026)

### Step 1 — Record new PTZ values for reference flags
**Script:** `record_new_camera_flags.py`

We manually positioned the new camera at 3 known reference flags (92, 96, 106) using the camera's saved preset system. At each flag we read the live PTZ values from both the old (recorded) and new camera, and saved them side by side.

Output file: `PTZCamValues_181_new_raw.txt`
Format: `flag_num | old_pan | old_tilt | old_zoom | new_pan | new_tilt | new_zoom`

**Why:** We need real measurements from both cameras at the same physical points to derive a mathematical transformation between them.

---

### Step 2 — Derive transformation and generate new PTZ file
**Script:** `compute_ptz_transform.py`

Using the 3 reference measurements, this script fits a transformation model from old camera values → new camera values:

| Axis | Model | Result |
|------|-------|--------|
| Pan  | Constant offset | `new_pan = old_pan − 12.20` |
| Tilt | Linear (scale changed) | `new_tilt = 1.229 × old_tilt − 1.097` |
| Zoom | Linear (stronger zoom) | `new_zoom = 1.355 × old_zoom − 1.93` |

The script applies this transformation to all 48 original flag positions and writes the result to `PTZCamValues_181_2026.txt`.

**Why:** The pan offset is constant because the camera body is rotated the same amount at every angle. The tilt needed a linear model because the new camera has a different tilt gear ratio. Zoom also scaled linearly.

---

### Step 3 — Manual override for flags with bad original positions
**Script:** `override_flags_from_camera.py`

Some flags (125–134) had errors in the original PTZ values — their formula-derived positions were wrong. For these, we physically pointed the camera to the correct location and read the live PTZ directly from the camera.

We also added 4 **new flags** (135, 136, 137, 138) to cover areas of the colony that were previously not in the scan.

Usage: set `FLAGS_TO_OVERRIDE` at the top of the script, position the camera at the correct location for each flag, press Enter — the script reads the live PTZ and updates `PTZCamValues_181_2026.txt` in place. It saves after every flag so no progress is lost.

**Why:** The transformation formula only works when the original PTZ values were correct. For flags that were wrongly positioned in the original camera, the formula produces wrong results and manual correction is needed.

---

### Step 4 — Compute world angles and focal length (mod file)
**Notebook:** `draw_ptz_on_drone_chicks.ipynb`

This notebook reads `PTZCamValues_181_2026.txt` and converts the raw camera PTZ values to world-space angles and focal length using the south camera's calibration formulas:

```python
world_yaw   = new_pan + 38.23
world_pitch = (new_tilt + 1.017) / 1.2299 - 91.47
f           = 127.67 * new_zoom + 1120.5
```

The result is saved to `PTZCamValues181_mod.txt` — the file used by `real_coordinates_calculator.py` to project detections onto the drone image.

The notebook also visualizes all flag footprints on the drone image (saved as `flags_on_drone_2026.png`) so you can visually verify the coverage.

**Why:** The algorithm needs world-space angles and focal length (in pixels), not raw camera pan/tilt/zoom units. The calibration offsets were derived by comparing camera presets to known physical reference points on the colony.

---

## Flag Coverage — Final Result

The image below shows all 47 flag footprints projected onto the colony drone image, after the 2026 recalibration. Each colored rectangle represents the camera's field of view at that preset position.

![Flags on drone image](flags_on_drone_2026.png)

---

## Camera Scan Automation

The south camera performs two full scans per day. Each scan consists of two sequential tours:
- **Tour 1:** 32 flags (presets 92–119, 121, 122, 137, 123) — 15 seconds per flag
- **Tour 2:** 15 flags (presets 124–133, 135, 136, 138, 134, 1) — 15 seconds per flag

Scan times: **10:01:50** and **15:01:50** (Israel time, daily).

### Problem: the new camera UI can't set exact times
The camera's web interface only provides a coarse slider for scheduling — it cannot set times at the second level. The camera API also blocks writing the schedule configuration.

### Solution: external control via ONVIF
**Script:** `run_scan.py`

Instead of using the camera's internal schedule, this script runs on the PC and sends ONVIF `GotoPreset` commands directly to the camera at exact times. The camera has no internal schedule — the PC is the timer.

How it works:
1. Windows Task Scheduler triggers the script at 10:01:00 and 15:01:00
2. The script waits internally until the :50 second mark
3. It visits each preset in order, waiting 15 seconds at each one
4. Tour 1 runs first, then a 10-second gap, then Tour 2

Total scan duration: ~12 minutes (47 flags × 15s + 10s gap).

**Setup:** `setup_scan_tasks.ps1`
Run this PowerShell script once (right-click → Run with PowerShell) to register the two daily tasks in Windows Task Scheduler. The tasks run even when the user is logged out.

---

## Camera Utilities

### `explore_camera_schedule.py`
Exploration tool used to discover how the Dahua camera stores its tour schedule via HTTP CGI API. Queries many config sections and prints results. Used for reverse-engineering the camera's API during the 2026 recalibration work.

### `set_camera_schedule.py`
Reads the current tour schedule from the camera and can write new times. Note: this camera model blocks writing `PtzAutoMovement` config — the script can read but not apply changes. Kept for documentation and future firmware versions.

### `fix_camera_timezone.py`
The south camera had NTP disabled and was showing time 1 hour behind Israel time (UTC+2 instead of UTC+3 during summer). This script manually sets the camera clock to the correct Israel time (taken from the PC clock). Run it if the camera clock drifts again.

---

## File Reference

| File | Description |
|------|-------------|
| `PTZCamValues_181.txt` | Original (pre-2026) south camera PTZ values |
| `PTZCamValues_181_2026.txt` | New south camera PTZ values after replacement (raw pan/tilt/zoom) |
| `PTZCamValues_181_new_raw.txt` | Side-by-side old/new measurements for the 3 calibration reference flags |
| `PTZCamValues181_mod.txt` | South camera mod file: world pitch/yaw/f used by the algorithm |
| `PTZCamValues_191.txt` | North camera PTZ values (unchanged) |
| `PTZCamValues191_mod.txt` | North camera mod file |
| `real_coordinates_calculator.py` | Main algorithm: projects detections from camera pixel space to drone-image coordinates |
| `record_new_camera_flags.py` | Step 1: record new camera PTZ at reference flags |
| `compute_ptz_transform.py` | Step 2: derive transformation, generate PTZCamValues_181_2026.txt |
| `override_flags_from_camera.py` | Step 3: manually override specific flags from live camera |
| `draw_ptz_on_drone_chicks.ipynb` | Step 4: compute mod file and visualize flag coverage on drone image |
| `run_scan.py` | Daily scan controller via ONVIF (replace for camera's internal schedule) |
| `setup_scan_tasks.ps1` | Registers Windows Task Scheduler tasks for daily scans |
| `setup_scan_tasks.bat` | Alternative task registration (batch file version) |
| `fix_camera_timezone.py` | Fixes camera clock to Israel time |
| `set_camera_schedule.py` | Read/write camera tour schedule via Dahua HTTP API |
| `explore_camera_schedule.py` | Exploration tool for Dahua camera HTTP API |

---

## Camera Connection

Camera 181 (south) credentials are stored in `new_camera.ini` (not committed to git — contains password).

Format:
```ini
[General]
CAM_IP=2.54.101.27
CAM_PORT=8080
USER_NAME=admin
PASSWORD=...
```
