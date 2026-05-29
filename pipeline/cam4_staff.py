import cv2
import json
from datetime import datetime, timedelta
from ultralytics import YOLO

VIDEO_PATH = "data/CAM 4.mp4"
OUTPUT_PATH = "data/staff_events.jsonl"
STORE_CODE = "STORE_BLR_002"
CAMERA_ID = "CAM4"

print("Loading YOLO model...")
model = YOLO("yolov8n.pt")

cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    print("ERROR: Could not open CAM4 video.")
    exit()

fps = cap.get(cv2.CAP_PROP_FPS) or 25
base_time = datetime(2026, 4, 10, 10, 0, 0)

seen_ids = set()
events = []
frame_count = 0

print("Processing CAM4 staff detection (backroom)...")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    if frame_count % 30 != 0:
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
                "event_type": "staff_seen",
                "track_id": int(person_id),
                "store_code": STORE_CODE,
                "camera_id": CAMERA_ID,
                "event_timestamp": timestamp.isoformat(),
                "is_staff": True,
            })

cap.release()

with open(OUTPUT_PATH, "w") as f:
    for e in events:
        f.write(json.dumps(e) + "\n")

print(f"\nDONE. Detected {len(events)} staff members in backroom (CAM4).")
print(f"Saved -> {OUTPUT_PATH}")