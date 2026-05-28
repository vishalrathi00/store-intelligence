import cv2
import json
from datetime import datetime, timedelta
from ultralytics import YOLO

VIDEO_PATH = "data/CAM 5.mp4"
OUTPUT_PATH = "data/cam5_queue_events.jsonl"
STORE_CODE = "ST1008"
CAMERA_ID = "CAM5"

print("Loading YOLO model...")
model = YOLO("yolov8n.pt")

cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    print("ERROR: Could not open CAM5 video.")
    exit()

fps = cap.get(cv2.CAP_PROP_FPS) or 25
base_time = datetime(2026, 4, 10, 10, 0, 0)

events = []
frame_count = 0
max_queue = 0

print("Processing CAM5 queue analytics...")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    if frame_count % 30 != 0:
        continue

    results = model(frame, classes=[0], verbose=False)
    queue_length = len(results[0].boxes)
    max_queue = max(max_queue, queue_length)

    timestamp = base_time + timedelta(seconds=frame_count / fps)

    events.append({
        "event_type": "queue",
        "store_code": STORE_CODE,
        "camera_id": CAMERA_ID,
        "event_timestamp": timestamp.isoformat(),
        "track_id": queue_length,
        "is_staff": False,
    })

cap.release()

with open(OUTPUT_PATH, "w") as f:
    for e in events:
        f.write(json.dumps(e) + "\n")

print(f"\nDONE. Generated {len(events)} queue events.")
print(f"Max queue length observed: {max_queue}")
print(f"Saved -> {OUTPUT_PATH}")