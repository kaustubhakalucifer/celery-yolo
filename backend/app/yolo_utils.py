import os.path
from typing import Any

import cv2

from backend.app.config import settings
from ultralytics import YOLO

# Load the YOLO model (globally, once per worker process)
try:
    print(f"Loading YOLO model: {settings.YOLO_MODEL_NAME}")
    model = YOLO(settings.YOLO_MODEL_NAME)
    print("YOLO model loaded successfully")
except Exception as e:
    print(f"Error loading YOLO model: {e}")
    model = None


def process_image_with_yolo(image_path: str) -> tuple[str, list[Any], str] | tuple[str, list[Any], None]:
    if not model:
        return "", [], "YOLO model not loaded."
    if not os.path.exists(image_path):
        return "", [], f"Image not found at {image_path}"
    try:
        img = cv2.imread(image_path)
        if img is None:
            return "", [], f"Could not read image: {image_path}"

        results = model(img)

        detections = []
        processed_img = img.copy()

        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                label = model.names[cls]

                detections.append({
                    "label": label,
                    "confidence": round(conf, 2),
                    "box": [x1, y1, x2, y2]
                })

                # Draw bounding box
                cv2.rectangle(processed_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                # Put label
                cv2.putText(processed_img, f"{label} {conf:.2}", (x1, y1 - 10), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 0.5,
                            (0, 255, 0), 2)

        base_name = os.path.basename(image_path)
        name, ext = os.path.splitext(base_name)
        processed_filename = f"{name}_processed{ext}"
        processed_image_full_path = os.path.join(settings.PROCESSED_IMAGE_DIR, processed_filename)

        cv2.imwrite(processed_image_full_path, processed_img)

        return processed_image_full_path, detections, None

    except Exception as a:
        print(f"Error processing image {image_path} with YOLO: {a}")
        return "", [], str(a)
