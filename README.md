# Project Title

Automatic Detecting and counting endangered colonial breeding terns using machine learning methods

## Description
In this project, we developed a fully automated deep-learning-based algorithm to identify, count, and map breeding seabirds, focusing on two tern species in Israel: the vulnerable Common Tern (Sterna hirundo) and the endangered Little Tern (Sternula albifrons) in a challenging environment, in a large and densely populated breeding colony containing breeding pairs of two visually similar species. Using YOLOv8 for initial object detection, we enhanced classification performance by integrating ecological and behavioral features, including spatial fidelity, movement patterns, and size through camera calibration techniques.
For a detailed description of the methods and results, please refer to our paper.

## Mapping Camera Positions to Real-World Coordinates
We setup preset camera positions with specific zoom, yaw and pitch settings, enabling automated scanning tours at predefined intervals and times between the present positions location. 
Automated scans were conducted multiple times daily. Each camera focused on its designated area, with combined coverage of the entire island.  
The cameras were calibrated using a drone image of the colony anchored to geographic coordinates. By utilizing the drone image along with recorded zoom levels, pitch, and yaw for each frame, we calculated the precise location of each pixel on the island. This calibration allowed us to convert pixel dimensions into centimeters, enabling the actual size of each bounding box to be calculated and incorporated as a feature in the classifier.  
In this section, we describe the code parts that facilitate to map the camera positions into real-world coordinates.

### Fetch camera positions PTZ parameters
We use Python script (get_camera_ptz.py) to fetch the preset position PTZ parameters (zoom, pitch, and yaw) of the camera. The script should be executed while the scan is triggered and uses Dahua camera external API to fetch details. 

#### Script usage
1. Navigate to the RealCoordinatesCalculator directory.
2. Specify camera details in get_camera_ptz.ini.
3. Run get_camera_ptz.py script with argument of delay (in seconds) between position change. 
```bash
Python get_camera_ptz.py -s 15
```

The script saves all PTZ details in a text file.


### Camera PTZ adjusments
In draw_ptz_on_drone.ipynb Notebook, we calibrate the camera to map positions into the real-world coordinates. We made small adjustments to the values based on deviations observed in the positions mapping on the island area. The notebook visualizes all positions' areas on drone image.

### Detecting Overlaps Between Position Areas
The detect_overlaps.ipynb notebook identifies overlaps between camera positions to prevent multiple counts of the same tern from different camera positions.  
The script saves all redundant areas in a JSON file (overlap_areas.json), which is used later when counting terns.


## Models training process

### Training YOLOv8 for Species Detection
We fine-tuned a YOLOv8 model to distinguish between Common Terns and Little Terns using their physical characteristics.
A Jupyter Notebook (training_YOLOv8.ipynb) is provided to facilitate training using Ultralytics' YOLOv8. The training command is executed within the notebook to fine-tune the model on our dataset.

#### Notebook Usage
1. Navigate to the YoloDetector directory.
2. Open the training_YOLOv8.ipynb notebook.
3. Specify setting for run.
4. Run all cells to start training the model.

The trained model weights and logs are saved in the project output path defined in the Notebook.

### Training final classifier model to determine species
We create a range of features that represent the track of the tagged tern. These features include integrated outputs from the YOLOv8 model, movement rate and detection rate, location probability and box dimensions in centimers.

1. Run steps 1 to 3 from 'Running the Algorithm' section on the scans where the tagged images were captured. These steps create tern tracks.
2. Specify setting parameters in train_classifier.ini.
3. Open train_classifier.ipynb Notebook.
4. Run all cells.

This process associate tracks to the tagged terns and after that create all features that represents tracks. The notebook train and evaluate performance on multiple classifier models and saves the best-performing model.


## Running the Algorithm
To run the algorithm, follow these steps to execute each notebook in the correct order.

### Downloading Scans
To automatically download scans from both cameras twice a day, run extract_scans_auto.py in the ConvertVideoToImage directory.

### 1. run_video_converter_2025.ipynb Notebook: Video-to-Image Conversion and Position Categorization

This notebook converts video scans captured at the colony into images and detects camera switches to categorize the images by position. It supports a conversion of multiple scans within a video, organizing them into separate directories.

#### Notebook Usage
1. Navigate to the ConvertVideoToImage directory.
2. Specify the following settings in the run_video_converter.ini file:
   - **dates**: Dates you want to process.
   - **yolo_path**: Path to Yolo model used for detecting camera movement.
3. Specify the following settings in the tours_details.json file:
   - **videos_dir**: Path to the videos directory.
   - **images_dir**: Path to the output images directory.
4. Open the run_video_converter_2025.ipynb notebook.
5. Run all cells.

### 2. yolo_runner.ipynb Notebook: YOLO Object Detection on Images

This notebook applies the YOLO V8 object detection model to the categorized images from Notebook 1. The model is trained to detect the terns in each image. The results save for further analysis.

#### Notebook Usage
1. Navigate to the YoloDetector directory.
2. Specify the following settings in the yolo_runner.ini file:
   - **dates**: Dates on which you want to detect terns.
   - **images_dir**: Path to the input image directory.
   - **result_dir**: Path to the output YOLO detection results directory.
   - **images_chunk_size**: Number of images to process at one time in YOLO.
3. Open the yolo_runner.ipynb notebook.
4. Run all cells.

### 3. track_scan_runner.ipynb Notebook: Tracking Terns in a Single Scan
This notebook processes a one scan output from YOLO Object Detection to track individual terns across multiple images, creating a sequence of detections for each bird.

#### Notebook Usage
1. Navigate to the TrackingTerns directory.
2. Specify the following settings in the track_scan_runner.ini file:
   - **dates**: Dates on which you want to track terns.
   - **yolo_result_dir**: Path to the input YOLO results directory.
   - **tracker_result_dir**: Path to the output tracking results directory.
3. Open the track_scan_runner.ipynb notebook.
4. Run all cells.

## Option 1 - Daily Counting terns

### 4. daily_count_terns.ipynb Notebook: Daily Counting and Classifying Terns

This notebook classify and counts terns on colony on multiple one-scan outputs from one day. It makes aggregation of the results across different scans.

#### Notebook Usage
1. Navigate to the ClassifyTerns directory.
2. Specify the following settings in the daily_count_terns.ini file:
   - **date**: Date for which you want to classify and count terns.
   - **classifier_model**: Path to the trained classifier model.
   - **tracker_result_dir**: Path to the tracking results directory.
   - **labels_distribution**: Path to the label distributions statistics file.
3. Open the daily_count_terns.ipynb notebook.
4. Run all cells.

## Option 2 - Daily Detecting breeding terns

### 5. classify_terns.ipynb Notebook: Classifying Tracks
This notebook classify one-scan tracks detected in Notebook 3. The classifier is taken as input YOlO ouputs, track size in cm and location distribution. It saves the results on JSON files.

#### Notebook Usage
1. Navigate to the ClassifyTerns directory.
2. Specify the following settings in the classify_terns.ini file:
   - **date**: A date for which you want to classify terns.
   - **classifier_model**: Path to the trained classifier model.
   - **one_scan_result_dir**: Path to the input single-scan tracking results directory.
   - **classification_result_dir**: Path to the classifier results dir
   - **labels_distribution**: Path to the label distributions statistics file.
3. Open the classify_terns.ipynb notebook.
4. Run all cells.

### 6. track_breeding_terns_runner.ipynb Notebook: Tracking Breeding Terns

This notebook processes multiple one-scan outputs from part 3 to track terns across multiple scans. The tracks help identify breeding terns, which tend to remain in the same location over time.

#### Notebook Usage
1. Navigate to the TrackingTerns directory.
2. Specify the following settings in the track_breeding_terns_runner.ini file:
   - **date**: A date for which you want to track breeding terns.
   - **one_scan_result_dir**: Path to the input single-scan tracking results directory.
   - **mult_scans_result_dir**: Path to the output directory for multi-scan tracking results.
   - **classification_result_dir**: Path to the classifier results dir
   - **video_converter_dir**: Path to the images directory.
3. Open the track_breeding_terns_runner.ipynb notebook.
4. Run all cells.

### 7: report_breeding_terns.ipynb Notebook: Classifying and counting breeding terns
This notebook classifies and counts breeding terns within the colony, using tracking data from Part 5 as input.

#### Notebook Usage
1. Navigate to the FinalResults directory.
2. Specify the following settings in the report_breeding_terns.ini file:
   - **date**: Date for which you want to classify and count breeding terns.
   - **breeding_tracks_dir**: Path to the breeding terns tracking results directory.
   - **final_report_dir**: Path to the final breeding report result directory
   - **overlap_areas**: Path to the overlap areas file.
3. Open the report_breeding_terns.ipynb notebook.
4. Run all cells.
