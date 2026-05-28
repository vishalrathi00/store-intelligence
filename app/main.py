from fastapi import FastAPI

app = FastAPI(title="Store Intelligence API", version="1.0.0")


@app.get("/")
def root():
    return {"message": "Store Intelligence API is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "store-intelligence"}


@app.post("/events/ingest")
def ingest_events(events: list[dict]):
    return {"ingested": len(events), "status": "accepted"}


@app.get("/stores/{store_id}/metrics")
def get_metrics(store_id: str):
    return {
        "store_id": store_id,
        "unique_visitors": 0,
        "avg_dwell_seconds": 0,
        "conversion_rate": 0.0,
    }


@app.get("/stores/{store_id}/funnel")
def get_funnel(store_id: str):
    return {
        "store_id": store_id,
        "entered": 0,
        "browsed": 0,
        "queued": 0,
        "purchased": 0,
    }


@app.get("/stores/{store_id}/heatmap")
def get_heatmap(store_id: str):
    return {"store_id": store_id, "zones": []}


@app.get("/stores/{store_id}/anomalies")
def get_anomalies(store_id: str):
    return {"store_id": store_id, "anomalies": []}