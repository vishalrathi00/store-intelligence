# Design — Store Intelligence

## Problem

The goal is to turn raw CCTV footage from a physical retail store (Purplle, Brigade Road, Bangalore) into business metrics: how many people visited, where they spent time, how long the billing queue was, and how many visitors converted into buyers. The raw inputs are five camera feeds plus a point-of-sale (POS) transaction export and a store floor plan.

## System architecture

The system has three layers that are intentionally decoupled:

1. Pipeline layer (`pipeline/`) — reads video, runs detection and tracking, and emits structured events as JSONL. Each camera has a focused script so that one camera failing does not block the others.
2. API layer (`app/`) — a FastAPI service that ingests events and serves analytics. It is the only component the reviewer needs to run to see results. Every request is logged with a trace_id, store_id, endpoint, status code, and latency_ms for observability.
3. Storage layer — a SQLite event store. Every event (entry, queue, zone, purchase, staff) lands in one `events` table, which keeps the query logic for all metrics simple and uniform. A UNIQUE constraint on the natural key makes ingestion idempotent.

Data flows in one direction: video and POS data go into the pipeline, which produces events, which are POSTed to the ingestion API, which stores them, which the metrics endpoints then read.

## Camera mapping

I reviewed all five feeds and assigned each a role based on what it physically covers: CAM3 is the entry/exit door and drives footfall; CAM5 is the billing counter and drives queue analytics; CAM1 and CAM2 cover the shelf floor and drive zone analytics; CAM4 is the backroom and drives staff detection. Mapping cameras to roles by manual inspection was the foundation everything else builds on.

## Detection and tracking

I used YOLOv8 (the `yolov8n` model) for person detection because its ecosystem is Python-native and well documented, and ByteTrack (built into Ultralytics via `model.track`) for assigning a persistent ID to each person. Tracking is what makes unique-visitor counting possible — the same person across many frames is counted once, not once per frame.

## Metrics

Unique visitors come from distinct entry track IDs on CAM3, excluding anyone flagged as staff. Purchases come from deduplicated POS invoice numbers (101 line items collapse to 24 unique invoices). Zone heatmap counts distinct person-zone visits across the shelf cameras. Queue anomalies flag when the billing queue exceeds five people.

## Conversion correlation

Conversion follows the specification method: a visitor is counted as converted if billing-zone (CAM5) activity occurred within the 5-minute window before a POS transaction timestamp, correlated by store. This avoids treating every purchase as a guaranteed tracked conversion and instead ties purchases back to observed billing-area presence. In the processed sample the CAM5 footage window (~10:00–10:02) does not overlap the full-day POS transaction times, so the correlated converted count is 0 — the correlation logic is implemented and verifiable, but the sample windows do not intersect. Running the pipeline on full-length, time-aligned footage would populate this metric.

## Staff detection (CAM4)

Staff detection is implemented via CAM4 (backroom): persons tracked in the backroom feed are flagged `is_staff=true` and excluded from visitor counts (the metrics query filters `is_staff=0`). In the processed footage the backroom was effectively empty — at most one person appeared briefly, not long enough for the tracker to assign a stable ID — so no staff events were generated. The detection path runs and is verifiable; the sample simply had an empty backroom, which also means no genuine visitors were wrongly excluded as staff. The same mechanism handles the "all-staff clip" edge case: a feed dominated by staff would produce staff events that are filtered out of footfall.

## AI-assisted decisions

This project was built with AI assistance, which the challenge permits. I used AI to scaffold the FastAPI service, draft the detection and tracking loop, and design the SQLite schema. I reviewed and adjusted everything before committing: I chose the camera-to-role mapping myself after watching the footage, decided to deduplicate POS rows by invoice rather than count line items, implemented the 5-minute billing-window conversion correlation per the spec, and verified the queue maximum in the database before trusting the anomaly output. AI accelerated the boilerplate; the architecture and data decisions were mine to validate.

## Scope note

The challenge brief references "5 stores, 3 camera angles each." The dataset I received covered a single store (Purplle, Brigade Road) with five camera feeds, so I scoped the implementation to that one store (store code STORE_BLR_002). The pipeline and API are not hard-coded to one store — every event carries a store_code and all metrics queries filter by it, so adding more stores is a matter of running the same pipeline on their footage and ingesting the events. The single-store focus reflects the data available, not an architectural limit.
## Event schema note

Events use a simplified, consistent schema (event_type, track_id, store_code, camera_id, event_timestamp, zone_name, is_staff) rather than the full field set in the provided sample_events.jsonl. This keeps ingestion and querying uniform across all event types. Aligning field-for-field with the sample schema is a straightforward next step and would not change the pipeline or API logic.

## Limitations and future work

The visitor count reflects only the processed footage sample, while purchases reflect the full POS day, so the time windows do not fully intersect — this is documented transparently in the metrics response rather than hidden. Zones are approximated as three vertical frame regions rather than exact floor-plan polygons. Real-time streaming ingestion, stronger cross-camera re-identification, and richer anomaly detection are natural next steps. The architecture supports all of these via the same pipeline-to-API path.