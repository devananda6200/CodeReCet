from fastapi.testclient import TestClient

from app.main import app


def test_metrics_summary_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/metrics/summary")
    assert response.status_code == 200
    payload = response.json()
    assert "avg_fps" in payload
    assert "total_streams" in payload

