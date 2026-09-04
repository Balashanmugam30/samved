def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "samved-api"
    assert "timestamp" in data
    # Check correlation ID and latency headers
    assert "x-request-id" in response.headers
    assert "x-process-time-ms" in response.headers


def test_ready_check_dev_mode(client):
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
    assert data["mode"] == "DEV"
    assert "active_calls_count" in data
    assert "dependencies" in data
    assert "database" in data["dependencies"]
    assert "redis" in data["dependencies"]
    assert "telephony" in data["dependencies"]
    assert "speech" in data["dependencies"]
    assert "llm" in data["dependencies"]


def test_version_info(client):
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "samved-api"
    assert data["version"] == "0.1.0"
    assert data["mode"] == "DEV"
    assert data["problem_statement"] == "26093"
    assert "Phase 2" in data["phase"]


def test_v1_prefixed_endpoints(client):
    res_health = client.get("/v1/health")
    assert res_health.status_code == 200
    res_ready = client.get("/v1/ready")
    assert res_ready.status_code == 200


def test_structured_error_on_404(client):
    response = client.get("/nonexistent-endpoint-test")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert "message" in data["error"]
    assert "request_id" in data["error"]
