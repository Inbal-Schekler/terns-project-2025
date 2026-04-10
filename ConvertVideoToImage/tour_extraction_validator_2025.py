import os
import cv2
import json
import numpy as np
from skimage.metrics import structural_similarity as compare_ssim
from collections import defaultdict
import re
import matplotlib.pyplot as plt


#FINAL_FLAG_IMAGES_DIR = 'I:/My Drive/tern_project/Eyal/ConvertVideoToImage/FinalFlagSamples/2025'
FINAL_FLAG_IMAGES_DIR = '/content/drive/MyDrive/tern_project/Eyal/ConvertVideoToImage/FinalFlagSamples/2025'

class TourExtractionValidator:
    def __init__(self, threshold=0.09, camera_id=None):
        self._threshold = threshold
        self._camera_id = str(camera_id) if camera_id else None

        # Load flag metadata
        json_path = os.path.join(FINAL_FLAG_IMAGES_DIR, 'id_last.json')
        if not os.path.isfile(json_path):
            raise FileNotFoundError(f"Missing JSON file: {json_path}")

        with open(json_path, 'r') as f:
            key_areas_data = json.load(f)

        self._key_areas_data = key_areas_data

        # Validate or prepare for single camera or multiple
        if self._camera_id:
            if self._camera_id not in key_areas_data:
                raise ValueError(f"Camera ID {self._camera_id} not found.")
            self._init_camera(self._camera_id)
        else:
            self._references = {}
            for cam_id in key_areas_data:
                self._init_camera(cam_id, multi=True)

    def _init_camera(self, cam_id, multi=False):
        img_path = os.path.join(FINAL_FLAG_IMAGES_DIR, f'{cam_id}.jpg')
        if not os.path.isfile(img_path):
            raise FileNotFoundError(f"Reference image for {cam_id} not found at {img_path}")

        ref_img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if ref_img is None:
            raise ValueError(f"Could not load image for {cam_id}")

        flag_id = self._key_areas_data[cam_id]['flag_id']

        if multi:
            self._references[cam_id] = (ref_img, flag_id)
        else:
            self._reference_image = ref_img
            self._final_flag_id = flag_id

    def _compute_ssim(self, image1, image2):
        if image1.shape != image2.shape:
            image2 = cv2.resize(image2, (image1.shape[1], image1.shape[0]))
        score, _ = compare_ssim(image1, image2, full=True)
        return score

    def is_valid_tour(self, tour_dir):
        cam_id = self._camera_id or self._infer_cam_id(tour_dir)
        ref_img, final_flag_id = (
            (self._reference_image, self._final_flag_id) if self._camera_id
            else self._references[cam_id]
        )

        if not os.path.isdir(tour_dir):
            raise FileNotFoundError(f"Directory does not exist: {tour_dir}")

        def extract_frame_number(name):
            match = re.search(r'_(\d+)_', name)
            return int(match.group(1)) if match else -1

        last_flag_images = sorted(
            [os.path.join(tour_dir, f) for f in os.listdir(tour_dir)
             if str(final_flag_id) in f],
            key=extract_frame_number
        )

        if not last_flag_images:
            print(f"⚠️ No images for final flag {final_flag_id} in {tour_dir}")
            return False

        test_images = [last_flag_images[0], last_flag_images[-1]]

        for img_path in test_images:
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                print(f"⚠️ Could not read {img_path}")
                continue
            similarity = self._compute_ssim(ref_img, img)
            if similarity >= self._threshold:
                print(f"✅ Image {os.path.basename(img_path)} passed with SSIM {similarity:.3f}")
                return True

        print(f"❌ No images passed SSIM threshold {self._threshold}")
        return False

    def _infer_cam_id(self, tour_dir):
        for cam_id in self._key_areas_data:
            if cam_id in tour_dir:
                return cam_id
        raise ValueError("Camera ID could not be inferred from directory path.")


# === Executed only if script is run directly ===
def compare_reference_to_all_flags(tour_dir, reference_image, final_flag_id=None, threshold=0.15):
    import re
    from collections import defaultdict

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

    print("\n📊 SSIM values per flag:\n")

    for flag_num, images in sorted(flags_images.items()):
        # Pick the middle image
        images_sorted = sorted(images, key=lambda x: int(re.search(r'_(\d+)_', x).group(1)))
        mid_img_path = os.path.join(tour_dir, images_sorted[len(images_sorted) // 2])
        test_img = cv2.imread(mid_img_path, cv2.IMREAD_GRAYSCALE)

        if test_img is None:
            continue
        if reference_image.shape != test_img.shape:
            test_img = cv2.resize(test_img, (reference_image.shape[1], reference_image.shape[0]))

        score, diff = compare_ssim(reference_image, test_img, full=True)
        ssim_scores.append((flag_num, score))

        print(f"Flag {flag_num}: SSIM = {score:.4f} {'✅' if score >= threshold else '❌'}")

        # Only show image if this is the final flag
        if final_flag_id is not None and flag_num == final_flag_id:
            combined = np.hstack((reference_image, test_img))
            diff_normalized = (diff * 255).astype("uint8")

            plt.figure(figsize=(10, 4))
            plt.suptitle(f"Visual Comparison for Final Flag {flag_num}")

            plt.subplot(1, 2, 1)
            plt.title("Reference vs Sample")
            plt.imshow(combined, cmap='gray')
            plt.axis('off')

            plt.subplot(1, 2, 2)
            plt.title("SSIM Diff Map")
            plt.imshow(diff_normalized, cmap='gray')
            plt.axis('off')

            plt.tight_layout()
            plt.show()

    if ssim_scores:
        flags, scores = zip(*ssim_scores)
        plt.figure(figsize=(10, 6))
        plt.bar(flags, scores)
        plt.axhline(y=threshold, color='r', linestyle='--', label=f'Threshold {threshold}')
        plt.title("SSIM Scores per Flag")
        plt.xlabel("Flag Number")
        plt.ylabel("SSIM")
        plt.legend()
        plt.show()

    return ssim_scores

if __name__ == "__main__":
    tour_dir = "I:/My Drive/tern_project/Eyal/ConvertVideoToImage/ImagesDir/2025/atlitcam191_fixed.stream_2025-05-22_13_59_50/tour0"

    validator = TourExtractionValidator(camera_id='191', threshold=0.15)
    is_valid = validator.is_valid_tour(tour_dir)
    print("✅ Tour is valid." if is_valid else "❌ Tour is invalid.")

    # Full SSIM analysis — only prints values, and shows image for final flag only
    compare_reference_to_all_flags(
        tour_dir=tour_dir,
        reference_image=validator._reference_image,
        final_flag_id=validator._final_flag_id,
        threshold=validator._threshold
    )
