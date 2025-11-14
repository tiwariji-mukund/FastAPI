import pytest
import uuid
from unittest.mock import Mock, MagicMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from server.middleware.middleware import get_body, get_request_body, get_current_request_id
from server.middleware.middleware import _normalize_headers, _get_or_generate_request_id

def test_normalize_headers():
    """Test header normalization function."""
    headers = {
        "Content-Type": "application/json",
        "Content-Length": "100",
        "Authorization": "Bearer token123"
    }
    normalized = _normalize_headers(headers)
    
    assert "content-type" in normalized
    assert normalized["content-type"] == "application/json"
    assert "content-length" not in normalized  # Should be removed
    assert "authorization" in normalized

def test_get_or_generate_request_id_with_header():
    """Test request ID generation with existing header."""
    request = Mock()
    request.headers = {"X-Request-ID": "test-id-123"}
    
    request_id = _get_or_generate_request_id(request)
    assert request_id == "test-id-123"

def test_get_or_generate_request_id_without_header():
    """Test request ID generation without header."""
    request = Mock()
    request.headers = {}
    
    request_id = _get_or_generate_request_id(request)
    # Should generate a UUID
    assert isinstance(request_id, str)
    assert len(request_id) > 0
    # Should be a valid UUID format
    try:
        uuid.UUID(request_id)
    except ValueError:
        pytest.fail("Generated request ID is not a valid UUID")

def test_get_body_with_state():
    """Test get_body function with request.state.body."""
    # Create a simple object that allows attribute setting
    class MockState:
        def __init__(self):
            self.body = None
    
    request = type('Request', (), {})()
    request.__dict__ = {}
    request.state = MockState()
    request.state.body = {"test": "data"}
    
    body = get_body(request)
    assert body == {"test": "data"}

def test_get_body_with_direct_attribute():
    """Test get_body function with direct body attribute."""
    class MockState:
        def __init__(self):
            self.body = None
    
    request = type('Request', (), {})()
    request.__dict__ = {"body": {"test": "data"}}
    request.state = MockState()
    request.state.body = None
    
    body = get_body(request)
    assert body == {"test": "data"}

def test_get_body_fallback():
    """Test get_body function fallback to state."""
    class MockState:
        def __init__(self):
            self.body = None
    
    request = type('Request', (), {})()
    request.__dict__ = {}
    request.state = MockState()
    request.state.body = {"fallback": "data"}
    
    body = get_body(request)
    assert body == {"fallback": "data"}

def test_get_body_none():
    """Test get_body function when body is None."""
    class MockState:
        def __init__(self):
            self.body = None
    
    request = type('Request', (), {})()
    request.__dict__ = {}
    request.state = MockState()
    request.state.body = None
    
    body = get_body(request)
    assert body is None

