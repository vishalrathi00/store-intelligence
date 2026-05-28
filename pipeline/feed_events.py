import json
import requests

EVENTS_FILE = "data/events.jsonl"
API_URL = "http://localhost:8000/events/ingest"

events = []
with open(EVENTS_FILE) as f:
    for line in f:
        line = line.strip()
        if line:
            events.append(json.loads(line))

print(f"Sending {len(events)} events to API...")
response = requests.post(API_URL, json=events)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")