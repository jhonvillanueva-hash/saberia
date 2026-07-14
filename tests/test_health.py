import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test that the health endpoint returns 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data
