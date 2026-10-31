"""Tests for the health check endpoint."""


def test_health_check_returns_healthy(client):
    """Test /api/health returns 200 OK with healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "ORCA-FloodGuard"
    assert data["database_status"] == "connected"
    assert "timestamp" in data
    assert data["version"] == "1.0.0"


def test_root_endpoint(client):
    """Test / root endpoint returns welcome info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "docs" in data
    assert data["health"] == "/api/health"


def test_health_check_llm_diagnostics(client):
    """Test /api/health exposes LLM provider, actual model ID, and configuration status without exposing keys."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "llm_provider" in data
    assert data["llm_provider"] == "gemini"
    assert "llm_model_id" in data
    assert data["llm_model_id"] == "gemini-1.5-flash"
    assert "llm_configuration_status" in data
    assert data["llm_configuration_status"] in ("CONFIGURED", "NOT_CONFIGURED")
    assert "api_key" not in response.text.lower()
