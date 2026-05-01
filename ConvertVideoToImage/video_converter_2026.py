import os
import sys
import cv2
import re
import easyocr
from collections import defaultdict
from datetime import datetime

camera_move_time = defaultdict(lambda: 2, {
    27:5, 40: 4, 45: 4, 49: 6, 52: 6, 57: 4, 59: 4, 68: 5, 70:4, 71: 4, 72:5, 4: 5, 79: 4, 82: 5, 84: 5,
    94:3, 101:3, 103:3, 109:3, 110: 3, 111: 6, 117: 7, 119: 7, 123: 9, 127: 5, 136: 4
})

max_displayed_frames = defaultdict(lambda: 11, {
    73:9, 128:10, 138: 9
})

known_scan_start_times = {
    #"191": {"morning": "09:59:50", "noon": "14:59:50"},
    "191": {"morning": "10:00:10", "noon": "10:00:10"},
    #"181": {"morning": "10:01:50", "noon": "15:01:50"},
    "181": {"morning": "10:01:42", "noon": "15:01:42"},
}

reader = easyocr.Reader(['en'])


def normalize_timestamp_text(text):
    text = text.replace('*', ':').replace('/', '-').replace('â€“', '-').replace('â€”', '-')
    text = re.sub(r'[^0-9:\-.\s]', '', text)
    text = text.replace('.', ':')
    text = re.sub(r'\s+', ' ', text).strip()

    patterns = [
        (re.search(r'(\d{4})[-/](\d{2})[-/](\d{2})[^\d]?(\d{2}):(\d{2}):(\d{2})', text), '%Y-%m-%d %H:%M:%S', lambda g: f"{g[0]}-{g[1]}-{g[2]} {g[3]}:{g[4]}:{g[5]}"),
        (re.search(r'(\d{2})[-/](\d{2})[-/](\d{4})[^\d]?(\d{2}):(\d{2}):(\d{2})', text), '%d-%m-%Y %H:%M:%S', lambda g: f"{g[0]}-{g[1]}-{g[2]} {g[3]}:{g[4]}:{g[5]}"),
        (re.search(r'(\d{2})(\d{2})(\d{4})\s*(\d{2}):(\d{2}):(\d{2})', text),             '%d-%m-%Y %H:%M:%S', lambda g: f"{g[0]}-{g[1]}-{g[2]} {g[3]}:{g[4]}:{g[5]}"),
    ]

    for pattern, fmt, build in patterns:
        if pattern:
            try:
                return datetime.strptime(build(pattern.groups()), fmt)
            except ValueError:
                continue

    return None


def extract_timestamp_easyocr(frame, debug=False):
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = w - 430, 0, w, 60
    cropped = frame[y1:y2, x1:x2]
    result = reader.readtext(cropped, detail=0)
    text = " ".join(result)
    if debug:
        print(f"  [OCR raw] '{text}'")
    return normalize_timestamp_text(text)


class VideoConverter:
    def _seconds_to_frames(self, seconds):
        return int(seconds * 25)

    def _skip_seconds(self, video, seconds):
        for _ in range(self._seconds_to_frames(seconds)):
            ret, _ = video.read()
            if not ret:
                break

    def _skip_until_timestamp(self, video, camera_id, target_time_str, video_path):
        target_time = datetime.strptime(target_time_str, "%H:%M:%S")
        print(f"ðŸŽ¯ Target time: {target_time.time()}")

        max_checks = 60
        fps = 25
        first_detected_ts = None
        last_valid_frame_pos = None
        last_valid_time = None

        for check_num in range(max_checks):
            frame = None
            for _ in range(fps):
                ret, last_read_frame = video.read()
                if not ret:
                    print("âš ï¸ End of video reached before finding timestamp.")
                    return False
                frame = last_read_frame

            ts = extract_timestamp_easyocr(frame, debug=(check_num < 5))
            if not ts:
                print(f"  [check {check_num}] OCR read nothing parseable")
            if ts:
                detected_time = ts.time()
                if not first_detected_ts:
                    first_detected_ts = detected_time

                if detected_time == target_time.time():
                    print(f"ðŸ• First detected timestamp: {first_detected_ts}")
                    print(f"âœ… Reached target timestamp: {detected_time}")
                    return True

                if detected_time < target_time.time():
                    last_valid_time = detected_time
                    last_valid_frame_pos = video.get(cv2.CAP_PROP_POS_FRAMES)

                if detected_time > target_time.time():
                    break

        if last_valid_time and last_valid_frame_pos is not None:
            print(f"ðŸ• First detected timestamp: {first_detected_ts}")
            print(f"âš ï¸ Couldn't reach exact time. Rewinding to {last_valid_time}, frame {int(last_valid_frame_pos)}")
            video.set(cv2.CAP_PROP_POS_FRAMES, last_valid_frame_pos)
            t1 = datetime.combine(datetime.today(), last_valid_time)
            t2 = datetime.combine(datetime.today(), target_time.time())
            seconds_to_skip = (t2 - t1).total_seconds()
            print(f"â© Skipping ahead by {seconds_to_skip:.2f} seconds to reach target.")
            self._skip_seconds(video, seconds_to_skip)
            return True

        if first_detected_ts:
            print(f"ðŸ• First detected timestamp: {first_detected_ts}")
        print(f"âŒ Target timestamp {target_time.time()} not found or approximated.")
        return False

    def convert_video(self, video_path, flags_ids, tour_length, magin_between_tours,
                      margin_till_1st_tour, flags_to_shelve, output_dir):
        video = cv2.VideoCapture(video_path)
        fps = int(video.get(cv2.CAP_PROP_FPS))
        fps = 25 if fps <= 0 or fps > 60 else fps
        print(f"âš™ï¸ Detected FPS: {fps}")

        video_name = os.path.splitext(os.path.basename(video_path))[0]
        match = re.search(r'atlitcam(\d+)', video_name)
        camera_id = match.group(1) if match else 'unknown'

        hour_guess = int(video_name.split("_")[4])
        scan_type = "noon" if hour_guess >= 12 else "morning"
        target_time_str = known_scan_start_times[camera_id][scan_type]

        if not self._skip_until_timestamp(video, camera_id, target_time_str, video_path):
            print("âš ï¸ Skipping conversion due to invalid timestamp.")
            sys.exit(1)

        main_dir = f'{output_dir}/{camera_id}/{video_name}'
        os.makedirs(main_dir, exist_ok=True)
        print(f"ðŸ“‚ Created main directory: {main_dir}")
        sys.stdout.flush()

        for tour_num in range(2):
            if tour_num > 0:
                self._skip_seconds(video, magin_between_tours)

            tour_dir = f'{output_dir}/{camera_id}/{video_name}/tour{tour_num}/'
            os.makedirs(tour_dir, exist_ok=True)
            print(f"ðŸ“‚ Created tour directory: {tour_dir}")
            sys.stdout.flush()

            frame_num = 0
            frames_counter = 0
            flag_num = 0

            while flag_num < len(flags_ids):
                ret, curr_frame = video.read()
                if not ret:
                    print("Video ended before all flags were processed - extracting what was captured.")
                    break

                if frames_counter % fps == 0:
                    filename = f"flag{flags_ids[flag_num]}_{int(frame_num)}_{video_name}.jpg"
                    output_filename = f'{tour_dir}{filename}'
                    if flags_ids[flag_num] not in flags_to_shelve:
                        cv2.imwrite(output_filename, curr_frame)
                    frame_num += 1

                if frame_num > max_displayed_frames[flags_ids[flag_num]]:
                    self._skip_seconds(video, camera_move_time[flags_ids[flag_num]] + 3.34 - 0.461)
                    flag_num += 1
                    frame_num = 0

                frames_counter += 1

        video.release()
