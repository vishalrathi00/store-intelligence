# Design — Store Intelligence

## Problem

The goal is to turn raw CCTV footage from a physical retail store (Purplle, Brigade Road, Bangalore) into business metrics: how many people visited, where they spent time, how long the billing queue was, and how many visitors converted into buyers. The raw inputs are five camera feeds plus a point-of-sale (POS) transaction export and a store floor plan.

## System architecture

The system has three layers that are intentionally decoupled:

1. Pipeline layer (`pipeline/`) — reads video, runs detection and tracking, and emits structured events as JSONL. Each camera has a focused script so that one camera failing does not block the others.
2. API layer (`app/`) — a FastAPI service that ingests events and serves analytics. It is the only component the reviewer needs to run to see results.
3. Storage layer — a SQLite event store. Every event (entry, queue, zone, purchase) lands in one `events` table, which keeps the query logic for all metrics simple and uniform.

Data flows in one direction: video and POS data go into the pipeline, which produces events, which are POSTed to the ingestion API, which stores them, which the metrics endpoints then read.

## Camera mapping

I reviewed all five feeds and assigned each a role based on what it physically covers: CAM3 is the entry/exit door and drives footfall; CAM5 is the billing counter and drives queue analytics; CAM1 and CAM2 cover the shelf floor and drive zone analytics; CAM4 is the backroom. Mapping cameras to roles by manual inspection was the foundation everything else builds on.

## Detection and tracking

I used YOLOv8 (the `yolov8n` model) for person detection because its ecosystem is Python-native and well documented, and ByteTrack (built into Ultralytics via `model.track`) for assigning a persistent ID to each person. Tracking is what makes unique-visitor counting possible — the same person across many frames is counted once, not once per frame.

## Metrics

Unique visitors come from distinct entry track IDs on CAM3. Purchases come from deduplicated POS invoice numbers (101 line items collapse to 24 unique invoices). Conversion is purchases divided by visitors. Zone heatmap counts distinct person-zone visits across the shelf cameras. Queue anomalies flag when the billing queue exceeds five people.

## AI-assisted decisions

This project was built with AI assistance, which the challenge permits. I used AI to scaffold the FastAPI service, draft the detection and tracking loop, and design the SQLite schema. I reviewed and adjusted everything before committing: I chose the camera-to-role mapping myself after watching the footage, decided to deduplicate POS rows by invoice rather than count line items, and verified the queue maximum in the database before trusting the anomaly output. AI accelerated the boilerplate; the architecture and data decisions were mine to validate.

## Limitations and future work

The visitor count reflects only the processed footage sample, while purchases reflect the full POS day, so the raw conversion ratio overshoots 100% — this is documented transparently in the metrics response rather than hidden. Zones are approximated as three vertical frame regions rather than exact floor-plan polygons. CAM4 (backroom) is mapped for staff detection — to exclude staff from visitor counts — but was deprioritized in favor of completing documentation and tests. The architecture supports all of these via the same pipeline-to-API path.