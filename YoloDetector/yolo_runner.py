import os
import re
import sys
import glob
import json
import shutil
import argparse
import configparser
from PIL import Image
from roboflow import Roboflow
from ultralytics import YOLO


script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, os.pardir))
# Add the project root to the Python path
sys.path.append(project_root)
from Utilities.global_utils import GeneralUtils


parser = argparse.ArgumentParser()

parser.add_argument('-r', '--images_dir_name', help='Directory name where the JPG images are located')
args = parser.parse_args()
# Read the directory path where images located
images_dir_name = args.images_dir_name


config = configparser.ConfigParser()
# Read the config file
config.read('yolo_config.ini', encoding="utf8")
# Directory path where the yolo result will be located
images_dirs_path = config.get('General', 'images_dirs_path')
# Directory path where the yolo result will be located
result_dirs_path = config.get('General', 'result_dir_path')
# number of images to run on YOLO model in each iteration
images_chunk_size = int(config.get('General', 'images_chunk_size'))

# Path directory where the images are located
images_dir_path = f'{images_dirs_path}/{images_dir_name}'
# Path directory where the results will be located
results_dir_path = f'{result_dirs_path}/{images_dir_name}'

# Create directory for results
dir_utils = GeneralUtils()
dir_utils.create_directory(results_dir_path)
# Directories paths for the jsons and Images(with detection)
yolo_jsons_directory = f'{results_dir_path}/Jsons'
yolo_images_directory = f'{results_dir_path}/Images'
# Create dir for jsons
os.makedirs(yolo_jsons_directory)

# Retrieve all JPG image file paths in the directory
images_list = glob.glob(os.path.join(images_dir_path, "*.jpg"))

images_list = sorted(images_list, key=dir_utils.extract_flag_and_image_numbers)

# Load a model
model = YOLO(r'/content/drive/MyDrive/tern_project/Eyal/YoloDetector/TrainedVersions/Terns Detection 3.0.v3i.yolov8/terns-detection/weights/best.pt')  # pretrained YOLOv8n model

for start in range(0, len(images_list), images_chunk_size):
    end = start + images_chunk_size
    images_chunk = images_list[start:end]
    # predict images chunk in YOLO model
    results = model(images_chunk, show_conf=False, save=True, line_width=2, show_labels=True)

    for r in results:
        file_name = os.path.splitext(os.path.basename(r.path))[0]
        boxes = json.loads(r.tojson())
        # Get file name without extension
        json_result = {
            'predictions': boxes,
            'path' : r.path
        }

        with open(yolo_jsons_directory + "/" + file_name + ".json", "w") as file:
            # Write the JSON content to the file
            json.dump(json_result, file)

source_dir = './runs/detect/predict'
# Copy images directory to
# shutil.copytree(source_dir, os.path.join(yolo_images_directory, 'Images'))
shutil.copytree(source_dir, yolo_images_directory)
# remove /run directory
shutil.rmtree('./runs')