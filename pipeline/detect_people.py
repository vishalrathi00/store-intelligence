import cv2
from ultralytics import YOLO

VIDEO_PATH = "data/CAM 3.mp4"

print("Loading YOLO model...")
model = YOLO("yolov8n.pt")

print(f"Opening video: {VIDEO_PATH}")
cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    print("ERROR: Could not open video.")
    exit()

frame_count = 0
processed = 0

unique_ids = set()

while True:
    ret, frame = cap.read()

    if not ret:
        break

    frame_count += 1

    if frame_count % 30 != 0:
        continue

    processed += 1

    results = model.track(
        frame,
        persist=True,
        classes=[0],
        verbose=False
    )

    boxes = results[0].boxes
    people = len(boxes)

    if boxes.id is not None:
        ids = boxes.id.int().cpu().tolist()

        for person_id in ids:
            unique_ids.add(person_id)

    else:
        ids = []

    print(
        f"Frame {frame_count}: "
        f"{people} detected | "
        f"IDs: {ids} | "
        f"Unique visitors: {len(unique_ids)}"
    )

    if processed >= 20:
        break

cap.release()

print("\nFINAL SUMMARY")
print(f"Unique visitors detected: {len(unique_ids)}")