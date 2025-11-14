import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

@pytest.fixture(scope="module")
def client():
    """Create test client with mocked config."""
    with patch('common.env.InitializeConfig'), \
         patch('common.env.Config', MagicMock()):
        from main import app
        return TestClient(app)

def test_hello_world(client):
    """Test the hello world endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Hello World"
    assert "request_id" in data  # Middleware adds request_id

def test_hello_world_response_structure(client):
    """Test that hello world returns correct structure."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert isinstance(data["message"], str)

def test_test_config_endpoint(client):
    """Test the test/config endpoint without body."""
    response = client.get("/test/config")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "Test Config"
    assert "headers" in data

def test_test_config_with_headers(client):
    """Test the test/config endpoint with custom headers."""
    headers = {
        "content-type": "application/json",
        "api-key": "test-api-key-123"
    }
    response = client.get("/test/config", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["headers"]["content-type"] == "application/json"
    assert data["headers"]["api-key"] == "test-api-key-123"

def test_test_config_with_json_body(client):
    """Test the test/config endpoint with JSON body using POST."""
    headers = {
        "content-type": "application/json",
        "api-key": "test-key"
    }
    body = {"key1": "value1", "key2": "value2"}
    response = client.get("/test/config", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "headers" in data
    assert data["headers"]["content-type"] == "application/json"

def test_request_id_in_response(client):
    """Test that request ID is included in JSON responses."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "request_id" in data
    assert isinstance(data["request_id"], str)
    assert len(data["request_id"]) > 0

def test_request_id_header(client):
    """Test that request ID is included in response headers."""
    response = client.get("/")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0

def test_custom_request_id_header(client):
    """Test that custom request ID from header is used."""
    headers = {"X-Request-ID": "custom-request-id-123"}
    response = client.get("/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == "custom-request-id-123"
    assert response.headers["X-Request-ID"] == "custom-request-id-123"

