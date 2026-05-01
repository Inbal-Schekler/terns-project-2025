import os
import re
import json
import argparse
import sys

from pathlib import Path
from datetime import datetime

from video_converter_2026 import VideoConverter


def get_tour_details(video_path, tours_details):
    pattern = r'atlit(?:cam)?(\d+)'
    match = re.search(pattern, video_path)

    if match:
        camera_id = match.group(1)
        specific_cam_details = None
        for _, cam_details in tours_details.items():
            if cam_details["camera_id"] == int(camera_id):
                specific_cam_details = cam_details
                break
        if specific_cam_details is None:
            raise ValueError("Camera ID not found in tours_details")
    else:
        raise ValueError("Camera ID could not be extracted from filename")

    flags_ids = specific_cam_details['flags_ids']
    tour_length = specific_cam_details['tour_length']
    magin_between_tours = specific_cam_details['magin_between_tours']
    margin_till_1st_tour = specific_cam_details['margin_till_1st_tour']
    flags_to_shelve = specific_cam_details.get('flags_to_shelve', [])

    return (flags_ids, tour_length, margin_till_1st_tour, magin_between_tours, flags_to_shelve)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--video_name', help='The name of a video')
    video_name = parser.parse_args().video_name

    json_path = os.path.abspath('tours_details.json')
    with open(json_path, 'r', encoding='utf-8') as config_file:
        tour_configuration = json.load(config_file)

    videos_dir = Path(tour_configuration["videos_dir"])
    if not videos_dir.exists() or not videos_dir.is_dir():
        print(f'{videos_dir} - Movies directory path does not exist.')
        exit()

    video_path = str(videos_dir / video_name)

    video_converter = VideoConverter()
    (flags_ids, tour_length, margin_till_1st_tour, magin_between_tours, flags_to_shelve) = \
        get_tour_details(video_path, tour_configuration['tours_details'])

    if flags_ids is None or tour_length is None:
        print("❌ Could not extract tour details — exiting.")
        sys.stdout.flush()
        exit()

    video_converter.convert_video(video_path, flags_ids, tour_length, magin_between_tours,
                                  margin_till_1st_tour, flags_to_shelve,
                                  tour_configuration['images_dir'])
