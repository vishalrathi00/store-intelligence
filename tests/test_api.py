"""
Tests for the Store Intelligence API.

AI prompt used: "Write pytest tests for a FastAPI app with endpoints for
health, event ingestion, metrics, funnel, heatmap, and anomalies. Cover
happy paths and edge cases like an empty/unknown store."
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "message" in r.json()


def test_ingest_events():
    events = [
        {
            "event_type": "entry",
            "track_id": 9001,
            "store_code": "TEST_STORE",
            "camera_id": "CAM3",
            "event_timestamp": "2026-04-10T10:00:00",
            "is_staff": False,
        }
    ]
    r = client.post("/events/ingest", json=events)
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"
    assert r.json()["ingested"] == 1


def test_ingest_empty_list():
    r = client.post("/events/ingest", json=[])
    assert r.status_code == 200
    assert r.json()["ingested"] == 0


def test_metrics_structure():
    r = client.get("/stores/TEST_STORE/metrics")
    assert r.status_code == 200
    data = r.json()
    assert "unique_visitors" in data
    assert "purchases" in data
    assert "conversion_rate_percent" in data


def test_metrics_unknown_store():
    r = client.get("/stores/NONEXISTENT/metrics")
    assert r.status_code == 200
    data = r.json()
    assert data["unique_visitors"] == 0
    assert data["conversion_rate_percent"] == 0.0


def test_funnel_structure():
    r = client.get("/stores/TEST_STORE/funnel")
    assert r.status_code == 200
    data = r.json()
    assert "entered" in data
    assert "purchased" in data


def test_heatmap_structure():
    r = client.get("/stores/TEST_STORE/heatmap")
    assert r.status_code == 200
    assert "zones" in r.json()


def test_anomalies_structure():
    r = client.get("/stores/TEST_STORE/anomalies")
    assert r.status_code == 200
    assert "anomalies" in r.json()


def test_ingest_idempotent():
    """Re-ingesting the same event should not double-count."""
    event = [
        {
            "event_type": "entry",
            "track_id": 9999,
            "store_code": "IDEM_STORE",
            "camera_id": "CAM3",
            "event_timestamp": "2026-04-10T11:00:00",
            "is_staff": False,
        }
    ]
    client.post("/events/ingest", json=event)
    client.post("/events/ingest", json=event)
    r = client.get("/stores/IDEM_STORE/metrics")
    assert r.json()["unique_visitors"] == 1