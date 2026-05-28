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
    visitors = conn.execute(
        """SELECT COUNT(DISTINCT track_id) AS c
           FROM events
           WHERE store_code = ? AND event_type = 'entry' AND is_staff = 0""",
        (store_id,),
    ).fetchone()["c"] or 0

    purchases = conn.execute(
        """SELECT COUNT(*) AS c
           FROM events
           WHERE store_code = ? AND event_type = 'purchase'""",
        (store_id,),
    ).fetchone()["c"] or 0
    conn.close()

    conversion = round((purchases / visitors) * 100, 1) if visitors > 0 else 0.0

    return {
        "store_id": store_id,
        "unique_visitors": visitors,
        "purchases": purchases,
        "conversion_rate_percent": conversion,
        "avg_dwell_seconds": 0,
        "note": "Visitors from processed footage sample; purchases from full-day POS. See DESIGN.md.",
    }


@app.get("/stores/{store_id}/funnel")
def get_funnel(store_id: str):
    conn = get_connection()
    entered = conn.execute(
        """SELECT COUNT(DISTINCT track_id) AS c
           FROM events
           WHERE store_code = ? AND event_type = 'entry' AND is_staff = 0""",
        (store_id,),
    ).fetchone()["c"] or 0

    purchased = conn.execute(
        """SELECT COUNT(*) AS c
           FROM events
           WHERE store_code = ? AND event_type = 'purchase'""",
        (store_id,),
    ).fetchone()["c"] or 0
    conn.close()

    return {
        "store_id": store_id,
        "entered": entered,
        "browsed": 0,
        "queued": 0,
        "purchased": purchased,
    }


@app.get("/stores/{store_id}/heatmap")
def get_heatmap(store_id: str):
    conn = get_connection()
    rows = conn.execute(
        """SELECT zone_name, COUNT(*) AS visits
           FROM events
           WHERE store_code = ? AND event_type = 'zone_entered'
           GROUP BY zone_name""",
        (store_id,),
    ).fetchall()
    conn.close()

    zones = [{"zone_name": r["zone_name"], "visits": r["visits"]} for r in rows]
    return {"store_id": store_id, "zones": zones}


@app.get("/stores/{store_id}/anomalies")
def get_anomalies(store_id: str):
    conn = get_connection()
    max_queue = conn.execute(
        """SELECT MAX(track_id) AS m
           FROM events
           WHERE store_code = ? AND event_type = 'queue'""",
        (store_id,),
    ).fetchone()["m"]
    conn.close()

    anomalies = []
    if max_queue and max_queue > 5:
        anomalies.append({
            "type": "long_queue",
            "detail": f"Queue length reached {max_queue}",
        })

    return {"store_id": store_id, "anomalies": anomalies}