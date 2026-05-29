import time
import uuid
import logging
import json
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from app.db import init_db, get_connection

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("store-intelligence")

app = FastAPI(title="Store Intelligence API", version="1.0.0")


@app.on_event("startup")
def startup():
    init_db()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    trace_id = str(uuid.uuid4())
    start = time.time()
    response = await call_next(request)
    latency_ms = round((time.time() - start) * 1000, 2)
    store_id = None
    parts = request.url.path.split("/")
    if "stores" in parts:
        idx = parts.index("stores")
        if idx + 1 < len(parts):
            store_id = parts[idx + 1]
    logger.info(json.dumps({
        "trace_id": trace_id,
        "store_id": store_id,
        "endpoint": request.url.path,
        "method": request.method,
        "status_code": response.status_code,
        "latency_ms": latency_ms,
    }))
    response.headers["X-Trace-Id"] = trace_id
    return response


def parse_ts(ts):
    if not ts:
        return None
    ts = ts.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S",
                "%d-%m-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    return None


def compute_converted(conn, store_id):
    purchases = conn.execute(
        "SELECT event_timestamp FROM events WHERE store_code=? AND event_type='purchase'",
        (store_id,),
    ).fetchall()
    queue_rows = conn.execute(
        "SELECT event_timestamp FROM events WHERE store_code=? AND event_type='queue'",
        (store_id,),
    ).fetchall()
    queue_times = [parse_ts(r["event_timestamp"]) for r in queue_rows]
    queue_times = [t for t in queue_times if t is not None]
    converted = 0
    for p in purchases:
        pt = parse_ts(p["event_timestamp"])
        if pt is None:
            continue
        for qt in queue_times:
            delta = (pt - qt).total_seconds()
            if 0 <= delta <= 300:
                converted += 1
                break
    return converted


@app.get("/")
def root():
    return {"message": "Store Intelligence API is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "store-intelligence"}


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    html_path = Path(__file__).parent / "dashboard.html"
    return html_path.read_text(encoding="utf-8")


@app.post("/events/ingest")
def ingest_events(events: list[dict]):
    conn = get_connection()
    inserted = 0
    for e in events:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO events
                   (event_type, track_id, store_code, camera_id,
                    event_timestamp, zone_name, is_staff)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    e.get("event_type"), e.get("track_id"), e.get("store_code"),
                    e.get("camera_id"), e.get("event_timestamp"),
                    e.get("zone_name"), 1 if e.get("is_staff") else 0,
                ),
            )
            inserted += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    logger.info(json.dumps({"event": "ingest", "event_count": len(events), "ingested": inserted}))
    return {"ingested": inserted, "status": "accepted"}


@app.get("/stores/{store_id}/metrics")
def get_metrics(store_id: str):
    conn = get_connection()
    visitors = conn.execute(
        "SELECT COUNT(DISTINCT track_id) AS c FROM events WHERE store_code=? AND event_type='entry' AND is_staff=0",
        (store_id,),
    ).fetchone()["c"] or 0
    purchases = conn.execute(
        "SELECT COUNT(*) AS c FROM events WHERE store_code=? AND event_type='purchase'",
        (store_id,),
    ).fetchone()["c"] or 0
    converted = compute_converted(conn, store_id)
    conn.close()
    conversion = round((converted / visitors) * 100, 1) if visitors > 0 else 0.0
    return {
        "store_id": store_id,
        "unique_visitors": visitors,
        "purchases": purchases,
        "converted_visitors": converted,
        "conversion_rate_percent": conversion,
        "avg_dwell_seconds": 0,
        "note": "Conversion uses spec method: a visitor is converted if billing-zone activity occurred within the 5-minute window before a purchase. See DESIGN.md.",
    }


@app.get("/stores/{store_id}/funnel")
def get_funnel(store_id: str):
    conn = get_connection()
    entered = conn.execute(
        "SELECT COUNT(DISTINCT track_id) AS c FROM events WHERE store_code=? AND event_type='entry' AND is_staff=0",
        (store_id,),
    ).fetchone()["c"] or 0
    browsed = conn.execute(
        "SELECT COUNT(DISTINCT track_id) AS c FROM events WHERE store_code=? AND event_type='zone_entered'",
        (store_id,),
    ).fetchone()["c"] or 0
    queued = conn.execute(
        "SELECT COUNT(*) AS c FROM events WHERE store_code=? AND event_type='queue'",
        (store_id,),
    ).fetchone()["c"] or 0
    purchased = conn.execute(
        "SELECT COUNT(*) AS c FROM events WHERE store_code=? AND event_type='purchase'",
        (store_id,),
    ).fetchone()["c"] or 0
    conn.close()
    return {"store_id": store_id, "entered": entered, "browsed": browsed, "queued": queued, "purchased": purchased}


@app.get("/stores/{store_id}/heatmap")
def get_heatmap(store_id: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT zone_name, COUNT(*) AS visits FROM events WHERE store_code=? AND event_type='zone_entered' GROUP BY zone_name",
        (store_id,),
    ).fetchall()
    conn.close()
    return {"store_id": store_id, "zones": [{"zone_name": r["zone_name"], "visits": r["visits"]} for r in rows]}


@app.get("/stores/{store_id}/anomalies")
def get_anomalies(store_id: str):
    conn = get_connection()
    max_queue = conn.execute(
        "SELECT MAX(track_id) AS m FROM events WHERE store_code=? AND event_type='queue'",
        (store_id,),
    ).fetchone()["m"]
    conn.close()
    anomalies = []
    if max_queue and max_queue > 5:
        anomalies.append({"type": "long_queue", "detail": f"Queue length reached {max_queue}"})
    return {"store_id": store_id, "anomalies": anomalies}