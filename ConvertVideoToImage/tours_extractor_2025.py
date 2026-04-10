import os
import re
import json
import glob
import argparse
import sys

from pathlib import Path
from datetime import datetime

from video_converter_2025 import VideoConverter


# For the process of assigning each image to the correct flag,
# we check that the last (or second-to-last) flag matches the expected image for that moment in time.
# We select areas in the image and compare their values.
# If they indeed match, the video was properly cut to the different flags.

def get_tour_details(video_path, tours_details):
    # Define a regular expression pattern to match the camera ID
    pattern = r'atlit(?:cam)?(\d+)'
    # Search for the pattern in the file path
    match = re.search(pattern, video_path)

    if match:
        camera_id = match.group(1)
        specific_cam_details = None
        for _, cam_detials in tours_details.items():
            if cam_detials["camera_id"] == int(camera_id):
                specific_cam_details = cam_detials
                break
        if specific_cam_details is None:
            raise ValueError("The file name does not have camera name as expected: {'191' or '181}")
    else:
        raise ValueError("The file name is not in the format to have the camera name as expected")

    flags_ids = specific_cam_details['flags_ids']
    tour_length = specific_cam_details['tour_length']
    magin_between_tours = specific_cam_details['magin_between_tours']
    margin_till_1st_tour = specific_cam_details['margin_till_1st_tour']

    # get the video time from the file name
    video_path_without_extension = os.path.splitext(video_path)[0]
    video_time = video_path_without_extension.split("_")[-3:]
    video_time = "_".join(video_time)

    time_format = "%H_%M_%S"
    try:
        video_time = datetime.strptime(video_time, time_format)
    except:
        return (None, None, None, None)

    return (flags_ids, tour_length, margin_till_1st_tour, magin_between_tours)


if __name__ == '__main__':

    #print("🚀 Script started")
    #sys.stdout.flush()

    parser = argparse.ArgumentParser()

    parser.add_argument('-r', '--video_name', help='The name of a video')
    # Read the directory path where videos located
    video_name = parser.parse_args().video_name

    # Read the JSON configuration file
    #with open('tours_details.json', 'r', encoding='utf-8') as config_file:
    json_path = os.path.abspath('tours_details.json')
    #print(f"🔍 Loading JSON from: {json_path}")
    #sys.stdout.flush()

    with open(json_path, 'r', encoding='utf-8') as config_file:

        tour_configuration = json.load(config_file)

    videos_dir = Path(tour_configuration["videos_dir"])

    if not videos_dir.exists() or not videos_dir.is_dir():
        print(f'{videos_dir} - Movies directory path does not exist.')
        exit()

    video_path = str(videos_dir / video_name)
    #print(f"📽️ Trying to open video at: {video_path}")
    #sys.stdout.flush()

    

    video_converter = VideoConverter()
    (flags_ids, tour_length, margin_till_1st_tour, magin_between_tours) = get_tour_details( \
        video_path, tour_configuration['tours_details'])

    if flags_ids == None or tour_length == None:
        print("❌ Could not extract tour details — exiting.")
        sys.stdout.flush()
        exit()

    video_converter.convert_video(video_path, flags_ids, tour_length, magin_between_tours, \
                                  margin_till_1st_tour, tour_configuration['images_dir'])




