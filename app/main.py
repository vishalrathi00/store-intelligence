from fastapi import FastAPI
from app.db import init_db, get_connection

app = FastAPI(title="Store Intelligence API", version="1.0.0")


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"message": "Store Intelligence API is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "store-intelligence"}


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
                    e.get("event_type"),
                    e.get("track_id"),
                    e.get("store_code"),
                    e.get("camera_id"),
                    e.get("event_timestamp"),
                    e.get("zone_name"),
                    1 if e.get("is_staff") else 0,
                ),
            )
            inserted += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return {"ingested": inserted, "status": "accepted"}


@app.get("/stores/{store_id}/metrics")
def get_metrics(store_id: str):
    conn = get_connection()
    row = conn.execute(
        """SELECT COUNT(DISTINCT track_id) AS visitors
           FROM events
           WHERE store_code = ? AND event_type = 'entry' AND is_staff = 0""",
        (store_id,),
    ).fetchone()
    conn.close()
    return {
        "store_id": store_id,
        "unique_visitors": row["visitors"] or 0,
        "avg_dwell_seconds": 0,
        "conversion_rate": 0.0,
    }


@app.get("/stores/{store_id}/funnel")
def get_funnel(store_id: str):
    return {"store_id": store_id, "entered": 0, "browsed": 0, "queued": 0, "purchased": 0}


@app.get("/stores/{store_id}/heatmap")
def get_heatmap(store_id: str):
    return {"store_id": store_id, "zones": []}


@app.get("/stores/{store_id}/anomalies")
def get_anomalies(store_id: str):
    return {"store_id": store_id, "anomalies": []}