
import os
import sys
import cv2
import json
import configparser
#from Utilities.global_utils import GeneralUtils
from collections import defaultdict
import shutil


from tour_extraction_validator_2025 import TourExtractionValidator

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, os.pardir))
# Add the project root to the Python path
sys.path.append(project_root)


camera_move_time = defaultdict(lambda: 2, {
    27:5, 40: 4, 45: 4, 49: 6, 52: 6, 57: 4, 59: 4, 68: 5,70:4, 71: 4, 72:5, 4: 5, 79: 4, 82: 5, 84: 5,
    94:3,101:3,103:3,109:3,110: 3,111: 6, 117: 7, 119: 7, 123: 9, 127: 5, 136: 4
})

max_displayed_frames = defaultdict(lambda: 11, {
    73:9, 128:10, 138: 9
})


class VideoConverter:
    def __init__(self):
        config = configparser.ConfigParser()
        # Read the config file
        config.read('run_video_converter.ini', encoding="utf8")
        # Load a model
        #yolo_path = config.get('General', 'yolo_path').replace('\\', '/')
        # Check if model file exists
        #if not os.path.exists(yolo_path):
        #    print(f"Model path does not exist: {yolo_path}")
        #   exit()

        self._tour_extract_validator = TourExtractionValidator()


    def _seconds_to_frames(self, seconds_number):
        return seconds_number * 25

#    def _skip_seconds(self, video, seconds_number):
#        frames_num = self._seconds_to_frames(seconds_number)  # Get frames number in the seconds ammount
#        success = True
#        counter = 0
#        while success and counter < frames_num:
#            success, _ = video.read()
#           counter = counter + 1



    def _skip_seconds(self, video, seconds):
        """Skip a number of seconds in the video."""
        frames_to_skip = int(self._seconds_to_frames(seconds))
        for _ in range(frames_to_skip):
            success, _ = video.read()
            if not success:
                break


    # This function check how much tours the video length can fit
#    def _calc_tours_number(self, video_path, tour_length, fps):
#       # Open the video file
#        cap = cv2.VideoCapture(video_path)
#        # Check if the video file was opened successfully
#        if not cap.isOpened():
#            raise Exception("Error: Could not open video file")
#        # Get the total number of frames in the video
#        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
#        # Close the video file
#        cap.release()
#        # Calculate the video duration in seconds
#        video_duration = total_frames / fps
#        # Calculate the number of tours based on the tour length
#        return int(video_duration // tour_length)

    def convert_video(self, video_path, flags_ids, tour_length, magin_between_tours, \
                      margin_till_1st_tour, output_dir):
        # Open video file
        video = cv2.VideoCapture(video_path)

        if not video.isOpened():
            print(f"Error: Could not open video {video_path}")
            return

        flags_number = len(flags_ids)
        # Get the frame rate of the video
        fps = int(video.get(cv2.CAP_PROP_FPS))
        fps = 25 if fps == 1000 else fps
        tours_number = 2

        # Skip margin time before first tour start
        self._skip_seconds(video, margin_till_1st_tour)

        # Extract video name from path
        video_name = os.path.splitext(os.path.basename(video_path))[0]

        #utils_lib = GeneralUtils()
        #utils_lib.create_directory(f'{output_dir}/{video_name}')
        main_dir =  f'{output_dir}/{video_name}'
        os.makedirs(main_dir, exist_ok=True)
        print(f"📂 Created main directory: {main_dir}")
        sys.stdout.flush()

        for tour_num in range(tours_number):
            # Create dir for tour images
            tour_dir = f'{output_dir}/{video_name}/tour{tour_num}/'
            os.makedirs(tour_dir, exist_ok=True)
            print(f"📂 Created tour directory: {tour_dir}")
            sys.stdout.flush()

            if tour_num > 0:
                self._skip_seconds(video, magin_between_tours)

            frame_num = 0
            self._skip_seconds(video, 0)

            frames_counter = 0
            flag_num = 0

            while flag_num < flags_number:
                ret, curr_frame = video.read()

                if not ret:
                    print("❌ The video has missing frames, possibly caused by network issues during recording.")
                    sys.exit(1)

                if frames_counter % fps == 0:
                    filename = f"flag{flags_ids[flag_num]}_{int(frame_num)}_{video_name}.jpg"
                    output_filename = f'{output_dir}/{video_name}/tour{tour_num}/{filename}'

                    try:
                        cv2.imwrite(output_filename, curr_frame)
                    except Exception as e:
                        print(f"❌ Exception writing frame on tour {tour_num}: {e}")
                        sys.exit(1)

                    frame_num += 1

                    if frame_num > max_displayed_frames[flags_ids[flag_num]]:
                        self._skip_seconds(video, camera_move_time[flags_ids[flag_num]] + 3.34 - 0.461)
                        flag_num += 1
                        frame_num = 0

                frames_counter += 1

            # ✅ Validate the tour AFTER all flags are done
            try:
                is_valid = self._tour_extract_validator.is_valid_tour(tour_dir)
            except Exception as e:
                print(f"Error while validating tour {tour_dir}: {e}")
                is_valid = False

            if not is_valid:
                try:
                    if os.path.exists(tour_dir):
                        shutil.rmtree(tour_dir)
                        print(f"🗑️ Deleted invalid tour directory: {tour_dir}")
                except Exception as e:
                    print(f"❌ Error while deleting directory {tour_dir}: {e}")
                    sys.exit(1)

            # Delete video tours dir if all tours are invalid
            try:
                tours_dir = f'{output_dir}/{video_name}'
                if os.path.isdir(tours_dir) and len(os.listdir(tours_dir)) == 0:
                    shutil.rmtree(tours_dir)
                    print(f"🗑️ Deleted empty tour directory: {tours_dir}")
                    sys.exit(1)
            except Exception as e:
                print(f"❌ Error while deleting directory {tours_dir}: {e}")
                sys.exit(1)

        # Release the video file
        video.release()

if __name__ == "__main__":
    import json

    # === Load your JSON file ===
    json_path = r"I:\My Drive\tern_project\Eyal\ConvertVideoToImage\tours_details.json"  # Update if needed
    with open(json_path, "r") as f:
        config = json.load(f)

    videos_dir = r"I:\My Drive\tern_project\terns_movies\2025\181"
    images_dir = r"I:\My Drive\tern_project\Eyal\ConvertVideoToImage\ImagesDir\2025"
    tours_details = config["tours_details"]

    # === Select a specific camera to test ===
    camera_key = "181"  # 👈 Change to "181" to test the other

    # Get a video file name for the selected camera
    video_filename = f"atlitcam{camera_key}.stream_2025_05_23_10_01_50.mkv"  # 👈 Adjust this manually
    video_path = os.path.join(videos_dir, video_filename)

    # Extract parameters from the config
    tour_params = tours_details[camera_key]
    flags_ids = tour_params["flags_ids"]
    tour_length = tour_params["tour_length"]
    margin_till_first_tour = tour_params["margin_till_1st_tour"]
    magin_between_tours = tour_params["magin_between_tours"]

    print(f"📁 Using video: {video_path}")
    print(f"🏁 Flags: {len(flags_ids)}")
    print(f"🕓 Tour length: {tour_length} sec")
    print(f"⏩ Skipping {margin_till_first_tour} sec before first tour\n")

    # === Run the converter ===
    converter = VideoConverter()
    converter.convert_video(
        video_path=video_path,
        flags_ids=flags_ids,
        tour_length=tour_length,
        magin_between_tours=magin_between_tours,
        margin_till_1st_tour=margin_till_first_tour,
        output_dir=images_dir
    )



    print("🎬 Done converting and validating the video.")
