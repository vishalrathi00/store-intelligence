import cv2
import json
from datetime import datetime, timedelta
from ultralytics import YOLO

VIDEO_PATH = "data/CAM 2.mp4"
OUTPUT_PATH = "data/zone_events_cam2.jsonl"
STORE_CODE = "ST1008"
CAMERA_ID = "CAM2"

print("Loading YOLO model...")
model = YOLO("yolov8n.pt")

cap = cv2.VideoCapture(VIDEO_PATH)
if not cap.isOpened():
    print("ERROR: Could not open video.")
    exit()

fps = cap.get(cv2.CAP_PROP_FPS) or 25
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
base_time = datetime(2026, 4, 10, 10, 0, 0)


def get_zone(cx):
    if cx < width / 3:
        return "Left Shelf"
    elif cx < 2 * width / 3:
        return "Center Aisle"
    else:
        return "Right Shelf"


events = []
frame_count = 0
seen = set()

print("Processing CAM2 zone analytics...")

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
    xyxy = boxes.xyxy.cpu().tolist()
    timestamp = base_time + timedelta(seconds=frame_count / fps)

    for person_id, box in zip(ids, xyxy):
        cx = (box[0] + box[2]) / 2
        zone = get_zone(cx)
        key = (person_id, zone)
        if key not in seen:
            seen.add(key)
            events.append({
                "event_type": "zone_entered",
                "track_id": int(person_id),
                "store_code": STORE_CODE,
                "camera_id": CAMERA_ID,
                "zone_name": zone,
                "event_timestamp": timestamp.isoformat(),
                "is_staff": False,
            })

cap.release()

with open(OUTPUT_PATH, "w") as f:
    for e in events:
        f.write(json.dumps(e) + "\n")

print(f"\nDONE. Generated {len(events)} CAM2 zone events.")
print(f"Saved -> {OUTPUT_PATH}")