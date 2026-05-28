import cv2
import json
from datetime import datetime, timedelta
from ultralytics import YOLO

VIDEO_PATH = "data/CAM 3.mp4"
STORE_CODE = "ST1008"
CAMERA_ID = "CAM3"
OUTPUT_PATH = "data/events.jsonl"

print("Loading YOLO model...")
model = YOLO("yolov8n.pt")

cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    print("ERROR: Could not open video.")
    exit()

fps = cap.get(cv2.CAP_PROP_FPS) or 25
base_time = datetime(2026, 4, 10, 10, 0, 0)

seen_ids = set()
events = []
frame_count = 0

print("Processing video (full)...")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    if frame_count % 15 != 0:
        continue

    results = model.track(frame, persist=True, classes=[0], verbose=False)
    boxes = results[0].boxes

    if boxes.id is None:
        continue

    ids = boxes.id.int().cpu().tolist()
    timestamp = base_time + timedelta(seconds=frame_count / fps)

    for person_id in ids:
        if person_id not in seen_ids:
            seen_ids.add(person_id)
            events.append({
                "event_type": "entry",
                "track_id": int(person_id),
                "store_code": STORE_CODE,
                "camera_id": CAMERA_ID,
                "event_timestamp": timestamp.isoformat(),
                "is_staff": False,
            })

cap.release()

with open(OUTPUT_PATH, "w") as f:
    for event in events:
        f.write(json.dumps(event) + "\n")

print(f"\nDONE. Generated {len(events)} entry events.")
print(f"Unique visitors: {len(seen_ids)}")
print(f"Events written to: {OUTPUT_PATH}")