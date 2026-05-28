# CHOICES.md — Design Choices and Tradeoffs

# Key Choices — Store Intelligence

This document explains the major technical decisions made during implementation, the alternatives considered, and the tradeoffs accepted.

---

## 1. YOLOv8 + ByteTrack for Detection and Tracking

### Decision

Use the Ultralytics `yolov8n` model for person detection and the Ultralytics tracking workflow (`model.track(..., persist=True)`) backed by ByteTrack for assigning persistent person IDs.

### Alternatives Considered

* Detection-only approach (count boxes per frame)
* Larger YOLO variants (`yolov8s`, `yolov8m`)
* Re-identification pipelines for cross-camera identity matching

### Why This Choice

Detection alone cannot estimate unique visitors correctly because the same person appears across many frames and would be counted repeatedly.

Tracking solves this problem by assigning stable IDs across frames.

Example:

* Frame 30 → Person ID 2
* Frame 60 → Person ID 2
* Frame 90 → Person ID 2

This allows visitor counting using distinct IDs rather than frame counts.

I selected `yolov8n` specifically because it runs reasonably on CPU hardware, which is closer to what a reviewer environment is likely to provide.

### Tradeoff

The nano model prioritizes speed and accessibility over maximum detection accuracy.

A dedicated re-identification system could improve cross-camera matching but would introduce significantly more implementation complexity and validation risk.

---

## 2. SQLite with a Shared Events Table

### Decision

Use SQLite as the database and store all analytics events inside one shared `events` table.

Event types include:

* `entry`
* `queue`
* `zone_entered`
* `purchase`

### Alternatives Considered

* PostgreSQL in a separate Docker container
* Separate tables for each event category

### Why This Choice

SQLite is lightweight, file-based, Docker-friendly, and requires no external infrastructure.

Using one shared events table keeps analytics queries simple.

Examples:

* visitor counting → `COUNT(DISTINCT track_id)`
* heatmap analytics → `GROUP BY zone_name`
* anomaly detection → `MAX(track_id)`

The design also supports idempotent ingestion using a `UNIQUE` constraint so that replaying the same batch does not double-count events.

### Tradeoff

SQLite is ideal for prototype and local analytics workloads but is not optimized for high-concurrency production systems.

---

## 3. Event-Driven API Ingestion

### Decision

Pipelines generate JSONL events first and then POST them into `/events/ingest`.

Pipelines do not write directly into the database.

### Alternatives Considered

* Direct database writes from each pipeline script
* Tight coupling between computer vision processing and storage

### Why This Choice

This approach creates a clean separation between:

* computer vision processing
* API serving
* analytics storage

JSONL files become inspectable intermediate artifacts.

Benefits:

* easier debugging
* replayable ingestion
* simpler validation
* easier recovery after failures

A reviewer can inspect generated events independently from the database.

### Tradeoff

This introduces one additional step between video processing and metrics generation.

---

## 4. Deduplicating POS Data by Invoice

### Decision

Treat unique invoice numbers as purchases instead of counting raw CSV rows.

### Alternatives Considered

Count every POS row as an independent purchase.

### Why This Choice

The POS export contains multiple product rows per transaction.

Example:

* 101 CSV rows
* 24 unique invoices

Counting rows would inflate purchase counts and distort conversion analytics.

A purchase should represent a customer transaction, not an individual product line item.

I also chose to surface the visitor-versus-purchase time-window mismatch transparently in the metrics response rather than silently scaling numbers to look cleaner.

### Tradeoff

Purchase accuracy depends on invoice integrity in the source export.

---

## 5. Simplified Zone Mapping

### Decision

Use lightweight geometric zone segmentation based on horizontal frame position.

Zones:

* Left Shelf
* Center Aisle
* Right Shelf

### Alternatives Considered

* Manual polygon annotation
* Floor-plan calibrated coordinate mapping

### Why This Choice

The simplified approach provides meaningful zone analytics quickly without requiring extensive manual annotation.

It integrates naturally with CAM1 and CAM2 analytics and supports heatmap generation.

### Tradeoff

Geometric partitioning is an approximation.

Polygon-based calibration would produce more accurate spatial analytics.

---

## 6. AI Usage

### Decision

Use AI assistance for implementation acceleration while keeping architectural and data decisions human-reviewed.

### How AI Was Used

AI assistance was used for:

* scaffolding the FastAPI service
* drafting detection and tracking loops
* suggesting SQLite schema structure
* accelerating documentation and boilerplate generation

### Human Validation

All major technical and data decisions were reviewed and validated before being committed.

Examples include:

* manually assigning camera roles after inspecting footage
* choosing POS deduplication by invoice instead of counting raw rows
* selecting the simplified zone approximation approach
* validating queue maximum values directly from the SQLite database before trusting anomaly output

AI accelerated implementation speed and reduced boilerplate effort, but the architecture, tradeoff decisions, and analytical logic were actively reviewed and verified by me.

---

## Future Improvements

Potential future enhancements:

* CAM4 staff detection and exclusion
* realtime streaming ingestion
* stronger cross-camera re-identification
* richer anomaly detection
* dashboard layer for live monitoring
* cloud deployment
