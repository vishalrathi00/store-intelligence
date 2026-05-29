# How I Built This — Store Intelligence

A walkthrough of how I approached the challenge, the order I built things in, the problems I hit, and how I solved them. My background is backend engineering (Node.js / AWS); the computer-vision side was new to me, so part of this was learning as I went.

## My approach

I decided early on to build the system in thin, working layers rather than trying to perfect any single part first. The reasoning: a pipeline that runs end-to-end (video in, metrics out) is worth more than one polished component sitting next to broken ones. So the build order was deliberate — get the skeleton running, prove the acceptance gate, then add intelligence on top.

## Step 1 — Environment and skeleton

I set up Python 3.11, Docker Desktop (with WSL2 on Windows), and a private GitHub repo. The first real milestone was a FastAPI service exposing all six endpoints as stubs, then getting `docker compose up` to build and run it. Clearing the acceptance gate first meant everything I added afterwards was a bonus, not a risk.

A small but important early decision: I gitignored all data files (CCTV videos, the POS CSV, the floor plan) from the start. The POS export contains real customer names and phone numbers, and the videos are large and confidential, so none of that ever entered the repo history.

## Step 2 — Understanding the footage

Before writing detection code, I watched all five camera feeds and mapped each to a role based on what it physically covers:

- CAM3 → entry/exit door (footfall)
- CAM5 → billing counter (queue analytics)
- CAM1, CAM2 → shelf floor (zone analytics)
- CAM4 → backroom (staff detection)

This manual mapping was the foundation everything else builds on.

## Step 3 — Detection and tracking

I used YOLOv8 (`yolov8n`) for person detection and ByteTrack (via Ultralytics `model.track`) for persistent IDs. The key insight was that detection alone overcounts massively — the same person appears in hundreds of frames. Tracking solves this: unique visitors equal distinct track IDs. I confirmed this by watching the IDs stay stable across frames in my first test run (one person kept ID 2 across 20 frames, so the unique count correctly stayed at 2).

## Step 4 — Events to API to database

Rather than writing to the database directly from the pipeline, I had each pipeline script emit JSONL events, which are then POSTed to `/events/ingest`. This gave me inspectable intermediate files and a clean separation between CV processing and analytics serving. Events land in a single SQLite `events` table, which keeps every metric a simple SQL query. A UNIQUE constraint makes ingestion idempotent — I verified this by feeding the same batch twice and confirming the count did not double.

## Step 5 — Metrics, conversion, and POS

Unique visitors came from CAM3 entry events. For purchases I deduplicated the POS export by invoice number — 101 product line items collapsed to 24 actual transactions. Counting rows instead would have inflated purchases fourfold.

For conversion I implemented the spec method: a visitor counts as converted if billing-zone activity occurred within the 5-minute window before a transaction timestamp. In my processed sample the CAM5 window and the full-day POS times don't overlap, so the correlated count is 0 — I chose to surface this honestly in the response rather than fake a clean number.

## Step 6 — Zones, queue, and staff

Shelf cameras (CAM1, CAM2) feed a zone heatmap using a lightweight three-region split (left shelf / center aisle / right shelf), which avoided slow manual polygon annotation while still producing useful data. CAM5 produced queue-length events for anomaly detection. CAM4 ran staff detection — in this footage the backroom was effectively empty, which I documented rather than fabricating staff.

## Step 7 — Production readiness

I added structured logging (every request logs trace_id, store_id, endpoint, status, latency), wrote tests covering happy paths plus edge cases (empty store, unknown store, idempotent re-ingest), and added a live web dashboard at `/dashboard` showing metrics, the funnel, and the heatmap with auto-refresh.

## Problems I hit and how I solved them

- **WSL2 / Docker setup on Windows** was the biggest time sink — the WSL kernel was outdated and needed updating before Docker Desktop would start.
- **A stale Docker container** kept serving old code on port 8000 even after I updated the source. I found it with `netstat -ano | findstr :8000`, saw multiple processes on the port, and shut down the old container — the kind of debugging that only shows up in real deployments.
- **Store ID alignment** — the acceptance gate tests `STORE_BLR_002`; I aligned the pipeline and database to that store code.

## What I would do next

With more time: align the event schema exactly to the provided sample, add cross-camera re-identification so a person is the same identity across feeds, process full-length footage so the conversion time windows intersect, and extend to multiple stores (the architecture already filters every query by store_code, so this is a matter of running the pipeline on more footage).

## Honest summary

The acceptance gate passes fully and all parts (detection, API, production readiness, AI engineering, and the bonus dashboard) are implemented. The gaps that remain — exact schema match, cross-camera re-ID, single-store scope — are documented openly rather than hidden. I'd rather submit something that runs end-to-end with honest limitations than something that looks complete but doesn't hold up.