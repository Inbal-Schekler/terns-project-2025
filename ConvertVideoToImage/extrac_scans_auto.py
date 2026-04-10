import requests
import os
from datetime import datetime, timedelta
import subprocess

# Authentication credentials
username = "atlit"
password = "atlit121271"

# Path to FFmpeg executable
ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"

# Number of past days to download
days_to_download = 7

# Camera configurations
cameras = [
#cameras = [cam for cam in[
    {
        "name": "191",  # North camera
        "camera_id": "122e927a-b6ef-05a1-528e-ad11a9239ab2",
        "duration": 2280,
        "save_folder": r"I:\My Drive\tern_project\terns_movies\2025\191",
        "times_to_download": ["08:59:50", "13:59:50"]
    },
    {
        "name": "181",  # South camera
        "camera_id": "970f0a17-f47c-1356-1537-79ae8986c8b0",
        "duration": 1990,
        "save_folder": r"I:\My Drive\tern_project\terns_movies\2025\181",
        "times_to_download": ["10:01:50", "15:01:50"]
    }
]
#] if cam["name"] == "181"]

# Server details
server_ip = "212.179.113.90"
port = "7001"

# Process each camera
for cam in cameras:
    os.makedirs(cam["save_folder"], exist_ok=True)

    for day_offset in range(1, days_to_download + 1):
        target_date = datetime.now() - timedelta(days=day_offset)
        date_str = target_date.strftime("%Y_%m_%d")  # Use underscores in date

        for time_str in cam["times_to_download"]:
            time_parts = time_str.replace(":", "_")
            formatted_datetime = f"{date_str}_{time_parts}"
            final_file = f"atlitcam{cam['name']}.stream_{formatted_datetime}.mkv"
            final_path = os.path.join(cam["save_folder"], final_file)

            # Skip download if file already exists
            if os.path.exists(final_path):
                print(f"⏭️ Skipping: {final_path} already exists.")
                continue

            start_time = f"{target_date.strftime('%Y-%m-%d')}T{time_str}"
            url = f"http://{server_ip}:{port}/media/{cam['camera_id']}.mkv?pos={start_time}&duration={cam['duration']}"

            print(f"\n⬇️ Downloading video for camera {cam['name']} at {start_time}...")

            response = requests.get(url, auth=(username, password), stream=True)

            if response.status_code == 200:
                temp_file = os.path.join(cam["save_folder"], "temp_unseekable.mkv")
                with open(temp_file, "wb") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                print(f"✅ Downloaded temporary file: {temp_file}")

                print("🛠 Fixing video (making it seekable)...")
                ffmpeg_command = [ffmpeg_path, "-i", temp_file, "-c", "copy", final_path]

                try:
                    subprocess.run(ffmpeg_command, check=True)
                    print(f"✅ Fixed video saved as: {final_path}")
                    os.remove(temp_file)
                    print(f"🗑️ Deleted temporary file: {temp_file}")
                except subprocess.CalledProcessError as e:
                    print(f"❌ FFmpeg error: {e}")
            else:
                print(f"❌ Failed to download video. Status code: {response.status_code}")
                print("Response:", response.text)
