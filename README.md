# Store Intelligence — CCTV Retail Analytics

Converts raw CCTV footage from a retail store into business metrics: footfall, conversion rate, and billing-queue analytics. Built for the Brigade Road (Bangalore) store using YOLOv8 detection + tracking, a FastAPI service, and a SQLite event store.

## What it does

- Detects and tracks people in CCTV footage (YOLOv8 + ByteTrack)
- Generates structured events (entry, queue, zone) from video
- Correlates footfall with POS sales to compute conversion rate
- Exposes analytics via a REST API

## Camera mapping

| Camera | Role | Used for |
|--------|------|----------|
| CAM3 | Entry / Exit | Footfall (unique visitors) |
| CAM5 | Billing counter | Queue length analytics |
| CAM1, CAM2 | Shelves | Zone analytics |
| CAM4 | Backroom | Staff area (out of scope) |

## Architecture

```text
CCTV Videos / POS CSV
        |
        v
YOLOv8 Detection + Tracking
        |
        v
Event Generation (JSONL)
        |
        v
FastAPI Ingestion API
        |
        v
SQLite Event Store
        |
        v
Metrics / Funnel / Heatmap / Anomalies API
```

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1        # Windows
# source venv/bin/activate          # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt
pip install ultralytics opencv-python requests

# 3. Place data files in data/ (videos, POS csv) - not committed
# 4. Run the API
uvicorn app.main:app --reload
```

## Run with Docker

```bash
docker compose up --build
```

API available at `http://localhost:8000` — interactive docs at `http://localhost:8000/docs`.

## Live Dashboard (Part E)

After starting the API, open the live analytics dashboard at:http://localhost:8000/dashboard
It shows visitor metrics, the conversion funnel, and the zone heatmap, auto-refreshing every 5 seconds.

## Pipeline

```bash
# Generate entry events from CAM3
python pipeline/run_pipeline.py

# Load POS purchases
python pipeline/load_pos.py

# Generate queue events from CAM5
python pipeline/cam5_queue.py

# Generate zone events from CAM1
python pipeline/cam_zones.py

# Feed generated events into the API
python pipeline/feed_events.py
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health |
| POST | `/events/ingest` | Ingest events into the store |
| GET | `/stores/{store_id}/metrics` | Visitors, purchases, conversion rate |
| GET | `/stores/{store_id}/funnel` | Entry to purchase funnel |
| GET | `/stores/{store_id}/heatmap` | Zone visit counts |
| GET | `/stores/{store_id}/anomalies` | Queue anomaly detection |

## Notes

Data files (CCTV videos, POS records) are gitignored for size and confidentiality. See `docs/DESIGN.md` and `docs/CHOICES.md` for architecture decisions and assumptions.