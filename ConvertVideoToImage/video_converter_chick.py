import os
import cv2
import configparser

from tour_extraction_validator import TourExtractionValidator

class VideoConverter:
    def __init__(self, camera_id='191'):
        # Load config
        config = configparser.ConfigParser()
        config.read('run_video_converter.ini', encoding="utf8")

        # Validator to ensure correct extraction
        self._tour_extract_validator = TourExtractionValidator(camera_id=camera_id)

        # Assume 25 fps videos
        self.fps = 25

    def _seconds_to_frames(self, seconds):
        return int(seconds * self.fps)

    def _skip_seconds(self, video, seconds):
        """Skip a number of seconds in the video."""
        frames_to_skip = self._seconds_to_frames(seconds)
        for _ in range(frames_to_skip):
            success, _ = video.read()
            if not success:
                break

    def convert_video(self, video_path, flags_ids, output_dir):
        """Convert video to images, structured by flags."""
        video = cv2.VideoCapture(video_path)

        if not video.isOpened():
            print(f"Error: Could not open video {video_path}")
            return

        video_name = os.path.splitext(os.path.basename(video_path))[0]
        tour_dir = os.path.join(output_dir, video_name, 'tour0')
        os.makedirs(tour_dir, exist_ok=True)

        # Skip first 92 seconds
        self._skip_seconds(video, 92)

        for flag_num, flag_id in enumerate(flags_ids):
            # Skip first 2 seconds of camera movement
            # Adjust skip time: flags 15 and above need extra 2 seconds to allow focus
            if flag_id in [15,16,101,116]:
                skip_time = 4  # 2 original + 2 extra seconds
            else:
                skip_time = 2

            self._skip_seconds(video, skip_time)

            frames_to_capture = 11
            # 12 seconds available for capture between initial and final skip times
            frame_interval = (self._seconds_to_frames(12)) // frames_to_capture

            captured_frames = 0
            frame_counter = 0

            while captured_frames < frames_to_capture:
                success, frame = video.read()
                if not success:
                    break

                if frame_counter % frame_interval == 0:
                    image_filename = os.path.join(
                        tour_dir, f"flag{flag_id}_{captured_frames:02d}_{video_name}.jpg"
                    )
                    try:
                        cv2.imwrite(image_filename, frame)
                        captured_frames += 1
                    except Exception as e:
                        print(f"Error saving frame: {e}")

                frame_counter += 1

            # Skip last 1 second + margin between flags (3 seconds)
            self._skip_seconds(video, 1 + 3)
"""
        # Validate tour
        try:
            if not self._tour_extract_validator.is_valid_tour(tour_dir):
                print(f"Tour validation failed. Deleting {tour_dir}")
                for file in os.listdir(tour_dir):
                    os.remove(os.path.join(tour_dir, file))
                os.rmdir(tour_dir)
        except Exception as e:
            print(f"Validation error: {e}")

            video.release()
            print(f"Finished processing video {video_name}")
"""
# Example usage
if __name__ == "__main__":
    converter = VideoConverter(camera_id='191')
    converter.convert_video(
        video_path="I:/My Drive/tern_project/Chicks/movies/2025/atlitcam191_fixed.stream_2025-04-05_14_53_35.mkv",
        flags_ids=[7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,23,86,87,88,89,90,91,92,93,94,95,96,97
            ,98,99,100,101,7,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123],
        output_dir="I:/My Drive/tern_project/Chicks/images_mov"
    )
