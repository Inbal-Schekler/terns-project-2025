"""
This Python script processes YOLO object detection results stored in JSON files. It extracts class predictions and confidences for 
each flag, calculates the normalized class distribution, and saves the results in a sorted format. 
The final data is stored in 'labels_distribution_by_yolo.json'.
"""
import os
import json


# Initialize a dictionary to store the class distribution for each flag
class_distribution = {}

labels_list = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

# Define a function to process a single JSON file and update the class distribution
def process_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
        predictions = data['predictions']
        flag_number = data['path'].split('/')[-1].split('_')[0][4:]  # Extract flag number from file path

        if flag_number not in class_distribution:
            class_distribution[flag_number] = {}

        for prediction in predictions:
            class_number = prediction['class']
            confidence = prediction['confidence']
            if class_number not in class_distribution[flag_number]:
                class_distribution[flag_number][class_number] = 0
            class_distribution[flag_number][class_number] += confidence
        


jsons_dirs = [
    './../YoloDetector/YoloResults/atlitcam181.stream_2023_07_22_10_00_00/tour0/Jsons',
    './../YoloDetector/YoloResults/atlitcam191.stream_2023_07_22_10_00_00/tour0/Jsons'
]

# Iterate through files in dirs and process each file
for dir in jsons_dirs:
    for root, dirs, files in os.walk(dir):
        for file in files:
            if file.endswith('.json'):
                file_path = os.path.join(root, file)
                process_file(file_path)
        

# Calculate the total confidence for each flag
for flag_number in class_distribution:
    total_confidence = sum(class_distribution[flag_number].values())
    # Normalize the confidence values to percentages
    class_distribution[flag_number] = {class_number: (confidence / total_confidence) * 100
                                       for class_number, confidence in class_distribution[flag_number].items()}
    # Fill other labels with values of 0
    for label in labels_list:
        class_distribution[flag_number].setdefault(int(label), 0)
    
    # Sort the dictionary by keys
    class_distribution[flag_number] = {k: class_distribution[flag_number][k] for k in sorted(class_distribution[flag_number])}
    

# Sort the keys based on the numeric part of the flag names
sorted_keys = sorted(class_distribution.keys(), key=lambda x: int(x))

# Create a new dictionary with sorted keys
class_distribution = {key: class_distribution[key] for key in sorted_keys}

# Save the class distribution data to 'label_distribution_by_yolo.json'
with open('labels_distribution_by_yolo.json', 'w') as output_file:
    json.dump(class_distribution, output_file, indent=4)
