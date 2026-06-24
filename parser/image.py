from pathlib import Path
import cv2


def load_and_normalize_image(image_path: Path, target_width: int, target_height: int):
    image = cv2.imread(str(image_path))

    if image is None:
        raise ValueError(f"Bild konnte nicht geladen werden: {image_path}")

    return cv2.resize(image, (target_width, target_height))