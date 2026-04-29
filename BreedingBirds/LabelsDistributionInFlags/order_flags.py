# This script sorts the JSON data in 'label_distributions.json' file
# based on the numeric part of the flag names in ascending order.
# The sorted data is then saved back to the same file.

import json

# Read the JSON data from the file
with open('label_distributions.json', 'r') as file:
    data = json.load(file)

# Sort the keys based on the numeric part of the flag names
sorted_keys = sorted(data.keys(), key=lambda x: float(x[4:]))

# Create a new dictionary with sorted keys
sorted_data = {key: data[key] for key in sorted_keys}

# Write the sorted data back to the file
with open('label_distributions.json', 'w') as file:
    json.dump(sorted_data, file, indent=4)

print("JSON data has been sorted and saved back to 'label_distributions.json'.")
