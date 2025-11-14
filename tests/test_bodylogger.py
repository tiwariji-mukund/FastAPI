import pytest
from server.middleware.bodylogger import (
    filter_sensitive_headers,
    parse_request_body,
    parse_response_body
)

def test_filter_sensitive_headers():
    """Test filtering of sensitive headers."""
    headers = {
        "content-type": "application/json",
        "authorization": "Bearer token123",
        "api-key": "secret-key",
        "user-agent": "test-agent"
    }
    
    filtered = filter_sensitive_headers(headers)
    
    assert filtered["content-type"] == "application/json"
    assert filtered["user-agent"] == "test-agent"
    assert filtered["authorization"] == "***"
    assert filtered["api-key"] == "***"

def test_parse_request_body_json():
    """Test parsing JSON request body."""
    body_bytes = b'{"key": "value", "number": 123}'
    content_type = "application/json"
    
    parsed = parse_request_body(body_bytes, content_type)
    
    assert isinstance(parsed, dict)
    assert parsed["key"] == "value"
    assert parsed["number"] == 123

def test_parse_request_body_text():
    """Test parsing text request body."""
    body_bytes = b"plain text content"
    content_type = "text/plain"
    
    parsed = parse_request_body(body_bytes, content_type)
    
    assert isinstance(parsed, str)
    assert parsed == "plain text content"

def test_parse_request_body_invalid_json():
    """Test parsing invalid JSON falls back to string."""
    body_bytes = b'{"invalid": json}'
    content_type = "application/json"
    
    parsed = parse_request_body(body_bytes, content_type)
    
    assert isinstance(parsed, str)
    assert len(parsed) > 0

def test_parse_request_body_empty():
    """Test parsing empty body."""
    body_bytes = b""
    content_type = "application/json"
    
    parsed = parse_request_body(body_bytes, content_type)
    
    assert parsed is None

def test_parse_response_body_json():
    """Test parsing JSON response body."""
    body_bytes = b'{"status": "success", "data": {"id": 1}}'
    content_type = "application/json"
    
    parsed = parse_response_body(body_bytes, content_type)
    
    assert isinstance(parsed, dict)
    assert parsed["status"] == "success"
    assert parsed["data"]["id"] == 1

def test_parse_response_body_text():
    """Test parsing text response body."""
    body_bytes = b"HTML content here"
    content_type = "text/html"
    
    parsed = parse_response_body(body_bytes, content_type)
    
    assert isinstance(parsed, str)
    assert parsed == "HTML content here"

def test_parse_response_body_empty():
    """Test parsing empty response body."""
    body_bytes = b""
    content_type = "application/json"
    
    parsed = parse_response_body(body_bytes, content_type)
    
    assert parsed is None

