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

## Event schema note

Events use a simplified, consistent schema rather than the full field set in the provided sample_events.jsonl. This keeps ingestion and querying uniform across all event types. The simplified schema captures the same semantic fields as the sample; aligning names exactly is a rename/documentation change, not a logic change.

### Schema field mapping

| My field | Spec sample field | Notes |
|----------|-------------------|-------|
| event_type | event_type | Same |
| track_id | track_id / person_id | Persistent tracking ID |
| store_code | store_id | Store identifier |
| camera_id | camera_id | Same |
| event_timestamp | timestamp | ISO 8601 |
| zone_name | zone | Zone label for zone events |
| is_staff | is_staff | Staff exclusion flag |

## AI-assisted decisions

This project was built with a mix of my own work and AI assistance, which the challenge permits.

What I built and decided myself: I watched all five camera feeds and mapped each to its role manually. I wrote and iterated on several pipeline scripts directly — the CAM5 queue-length detection, the CAM1 and CAM2 zone segmentation logic, the CAM4 staff detection, and the POS deduplication-by-invoice approach. I designed the camera-agnostic, one-script-per-camera structure so a failure in one feed does not block the others. I refined the live dashboard layout and styling myself. And I debugged real runtime issues on my own, including a stale Docker container that kept serving old code on port 8000, which I traced using `netstat` and shut down.

Where AI helped: scaffolding the initial FastAPI service, drafting a first detection and tracking loop that I then adapted, suggesting the shape of the SQLite schema, and speeding up boilerplate and documentation.

How I validated AI output: I did not accept generated code blindly. I read it, ran it, and adjusted it. For example, I reworked the conversion logic to implement the spec's 5-minute billing-window correlation, chose to deduplicate POS rows by invoice rather than count line items, and verified the queue maximum directly in the database before trusting the anomaly endpoint. The architecture, the data decisions, and the judgment about what to keep, rewrite, or throw away were mine.

## Scope note

The challenge brief references "5 stores, 3 camera angles each." The dataset I received covered a single store (Purplle, Brigade Road) with five camera feeds, so I scoped the implementation to that one store (store code STORE_BLR_002). The pipeline and API are not hard-coded to one store — every event carries a store_code and all metrics queries filter by it, so adding more stores is a matter of running the same pipeline on their footage and ingesting the events. The single-store focus reflects the data available, not an architectural limit.

## Limitations and future work

The visitor count reflects only the processed footage sample, while purchases reflect the full POS day, so the time windows do not fully intersect — this is documented transparently in the metrics response rather than hidden. Zones are approximated as three vertical frame regions rather than exact floor-plan polygons. Cross-camera re-identification (same person identified across feeds), real-time streaming ingestion, and richer anomaly detection are natural next steps. The architecture supports all of these via the same pipeline-to-API path.