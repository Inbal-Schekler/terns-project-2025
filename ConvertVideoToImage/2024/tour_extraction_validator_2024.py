import os
import cv2
import json
import numpy as np
from skimage.metrics import structural_similarity as compare_ssim
import re
import matplotlib.pyplot as plt
from collections import defaultdict

# Path to final flag sample images
FINAL_FLAG_IMAGES_DIR = 'I:/My Drive/tern_project/Chicks/terns-project-chick/ConvertVideoToImage/2024/2024_FinalFlagSamples/'


class TourExtractionValidator:
    def __init__(self, threshold=0.15, camera_id='191'):
        """
        threshold: SSIM threshold between 0 and 1
        camera_id: ID of the camera (as string or int)
        """
        self._threshold = threshold
        self._camera_id = str(camera_id)

        # Load reference image for final flag
        reference_image_path = os.path.join(FINAL_FLAG_IMAGES_DIR, f'{self._camera_id}.jpg')
        if not os.path.isfile(reference_image_path):
            raise FileNotFoundError(f"Reference final flag image not found: {reference_image_path}")

        reference_image = cv2.imread(reference_image_path, cv2.IMREAD_GRAYSCALE)
        if reference_image is None:
            raise ValueError(f"Failed to load reference image: {reference_image_path}")

        # Load final flag ID from JSON
        json_path = os.path.join(FINAL_FLAG_IMAGES_DIR, 'chicks_key_areas.json')
        if not os.path.isfile(json_path):
            raise FileNotFoundError(f"Key areas JSON not found: {json_path}")

        with open(json_path, 'r') as file:
            content = file.read().strip()
            if not content:
                raise ValueError(f"Key areas JSON is empty: {json_path}")

            key_areas_data = json.loads(content)

        if self._camera_id not in key_areas_data:
            raise ValueError(f"Camera ID {self._camera_id} not found in key areas JSON.")

        self._final_flag_id = key_areas_data[self._camera_id]['flag_id']
        self._reference_image = reference_image

        print(
            f"✅ TourExtractionValidator initialized for camera {self._camera_id} with final flag {self._final_flag_id}")

    def _compute_ssim(self, image1, image2):
        """
        Compute the SSIM between two grayscale images.
        """
        # Resize images to the same size if necessary
        if image1.shape != image2.shape:
            image2 = cv2.resize(image2, (image1.shape[1], image1.shape[0]))

        score, _ = compare_ssim(image1, image2, full=True)
        return score

    def is_valid_tour(self, tour_dir):
        """
        Validate if the tour in the specified directory ends at the final flag.
        """
        if not os.path.exists(tour_dir):
            raise FileNotFoundError(f"Directory does not exist: {tour_dir}")

        # Get images that correspond to the final flag
        def extract_frame_number(filename):
            match = re.search(r'_(\d+)_', filename)
            return int(match.group(1)) if match else -1

        last_flag_images = sorted(
            [
                os.path.join(tour_dir, image_name)
                for image_name in os.listdir(tour_dir)
                if str(self._final_flag_id) in image_name
            ],
            key=lambda x: extract_frame_number(x)
        )

        if len(last_flag_images) == 0:
            print(f"⚠️ No images found for final flag ID {self._final_flag_id} in {tour_dir}")
            return False

        # Check first and last images of the final flag
        images_to_check = [last_flag_images[0], last_flag_images[-1]]

        for image_path in images_to_check:
            candidate_image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if candidate_image is None:
                print(f"⚠️ Warning: Could not read image {image_path}")
                continue

            # Compute SSIM and difference map
            similarity, diff = compare_ssim(self._reference_image, candidate_image, full=True)
            # print(f"🔍 SSIM for {os.path.basename(image_path)}: {similarity:.3f}")

            if similarity >= self._threshold:
                print(f"✅ Image {os.path.basename(image_path)} passed threshold with SSIM {similarity:.3f}")
                return True

        print(f"❌ No images passed SSIM threshold {self._threshold}. Tour is invalid.")
        return False


###comparing the values of SSM to all the other images

def compare_reference_to_all_flags(tour_dir, reference_image):
    def extract_flag_number(filename):
        match = re.search(r'flag(\d+)_', filename)
        return int(match.group(1)) if match else -1

    image_filenames = [f for f in os.listdir(tour_dir) if f.lower().endswith(('.jpg', '.png'))]

    flags_images = defaultdict(list)
    for f in image_filenames:
        flag_num = extract_flag_number(f)
        if flag_num != -1:
            flags_images[flag_num].append(f)

    ssim_scores = []

    print(f"\nComparing reference image to one sample image from each flag...\n")

    for flag_num, images in sorted(flags_images.items()):
        images_sorted = sorted(images, key=lambda x: int(re.search(r'_(\d+)_', x).group(1)))
        sample_image_filename = images_sorted[len(images_sorted) // 2]
        sample_image_path = os.path.join(tour_dir, sample_image_filename)

        sample_image = cv2.imread(sample_image_path, cv2.IMREAD_GRAYSCALE)
        if sample_image is None:
            continue

        if reference_image.shape != sample_image.shape:
            sample_image = cv2.resize(sample_image, (reference_image.shape[1], reference_image.shape[0]))

        # Compute SSIM and difference map
        score, diff = compare_ssim(reference_image, sample_image, full=True)
        ssim_scores.append((flag_num, score))

        print(f"Flag {flag_num}: SSIM = {score:.3f}")

        # ✅ Visualize reference and candidate image side by side
        combined = np.hstack((reference_image, sample_image))
        cv2.imshow(f"Flag {flag_num} - Reference (left) vs Sample (right)", combined)

        # ✅ Visualize SSIM difference map
        diff_normalized = (diff * 255).astype("uint8")
        cv2.imshow(f"Flag {flag_num} - SSIM Difference Map", diff_normalized)

        cv2.waitKey(0)  # Wait for key press to continue
        cv2.destroyAllWindows()

    if ssim_scores:
        flag_nums, scores = zip(*ssim_scores)
        plt.figure(figsize=(10, 6))
        plt.bar(flag_nums, scores)
        plt.xlabel('Flag Number')
        plt.ylabel('SSIM Score')
        plt.title('SSIM Scores of Flags Compared to Reference Image')
        plt.axhline(y=0.15, color='r', linestyle='--', label='Threshold 0.15')
        plt.legend()
        plt.show()

    return ssim_scores


if __name__ == "__main__":
    # === Test block ===
    # Replace with your tour directory path (folder with extracted images)
    tour_dir = "I:/My Drive/tern_project/Chicks/images_mov/2024"

    validator = TourExtractionValidator(camera_id='191', threshold=0.15)

    # ✅ Run distribution analysis
    compare_reference_to_all_flags(tour_dir, validator._reference_image)

    is_valid = validator.is_valid_tour(tour_dir)

    if is_valid:
        print("✅ Tour is valid. Final flag is correct.")
    else:
        print("❌ Tour is invalid. Final flag is missing or incorrect.")

