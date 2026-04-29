import os
import json
import argparse

# Function to calculate label probabilities for an image
def calculate_label_probabilities(labels):
    label_counts = {}
    total_objects = len(labels)
    
    for label in labels:
        label_id = int(label[0])
        if label_id not in label_counts:
            label_counts[label_id] = 0
        label_counts[label_id] += 1
    
    label_probabilities = {label_id: (count / total_objects) * 100 for label_id, count in label_counts.items()}
    return label_probabilities

# Function to process image files and create the desired JSON output
def process_directories(directories):
    image_probabilities = {}
    for directory in directories:
        for filename in os.listdir(directory):
            if filename.endswith('.txt'):
                image_name = os.path.splitext(filename)[0]
                with open(os.path.join(directory, filename), 'r') as file:
                    lines = file.readlines()
                    labels = [list(map(float, line.strip().split())) for line in lines]
                    label_probabilities = calculate_label_probabilities(labels)
                    image_probabilities[image_name] = label_probabilities
    return image_probabilities

# Main function to execute the script
def main():
    parser = argparse.ArgumentParser(description='Calculate label distributions for images in multiple directories.')
    parser.add_argument('-d', '--dirs', nargs='+', help='List of directories containing images and label files', required=True)
    args = parser.parse_args()

    directories = args.dirs
    image_probabilities = process_directories(directories)

    # Output the result to a JSON file
    output_file_path = 'label_probabilities.json'
    with open(output_file_path, 'w') as json_file:
        json.dump(image_probabilities, json_file, indent=4)
    
    print(f'Label probabilities have been calculated and saved to {output_file_path}')

if __name__ == "__main__":
    main()