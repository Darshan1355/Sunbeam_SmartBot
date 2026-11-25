import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert data["docs"] == "/docs"
    assert data["health"] == "/api/health"


def test_config_endpoint_safe():
    """Verify that public config endpoint does NOT leak secret API keys."""
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "app_name" in data
    assert "groq_model" in data
    assert "allowed_origins" in data
    # Ensure sensitive fields are strictly omitted
    assert "GROQ_API_KEY" not in data
    assert "api_key" not in data
    assert "secret" not in str(data).lower()


def test_cors_headers():
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_validation_error_format():
    """Verify centralized validation error response formatting."""
    response = client.post("/api/chat/completions", json={"invalid_field": 123})
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in data["error"]
