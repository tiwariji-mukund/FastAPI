from fastapi import Request
from fastapi.responses import Response
from typing import Dict, Optional, Tuple
import json
from server.logger import setup_logger
from common import constants as const

logger = setup_logger(__name__)

def filter_sensitive_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Filter sensitive headers from logging.
    
    Args:
        headers: Dictionary of headers
        
    Returns:
        Dictionary with sensitive headers masked as '***'
    """
    return {k: v if k.lower() not in const.SENSITIVE_HEADERS else '***' for k, v in headers.items()}

def parse_request_body(body_bytes: bytes, content_type: str) -> Optional[object]:
    """Parse request body based on content type.
    
    Args:
        body_bytes: Raw request body bytes
        content_type: Content-Type header value
        
    Returns:
        Parsed body (dict for JSON, string for other types) or None
    """
    if not body_bytes:
        return None
    
    if const.APPLICATION_JSON in content_type:
        try:
            return json.loads(body_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return body_bytes.decode("utf-8", errors="replace")[:500]
    else:
        return body_bytes.decode("utf-8", errors="replace")[:500]

def parse_response_body(body_bytes: bytes, content_type: str) -> Optional[object]:
    """Parse response body based on content type.
    
    Args:
        body_bytes: Raw response body bytes
        content_type: Content-Type header value
        
    Returns:
        Parsed body (dict for JSON, string for other types) or None
    """
    if not body_bytes:
        return None
    
    if const.APPLICATION_JSON in content_type:
        try:
            return json.loads(body_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return body_bytes.decode("utf-8", errors="replace")[:500]
    else:
        return body_bytes.decode("utf-8", errors="replace")[:500]

async def read_and_parse_request_body(request: Request) -> Tuple[Optional[object], Optional[bytes]]:
    """Read and parse request body from request.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Tuple of (parsed_body, raw_body_bytes)
    """
    request_body = None
    body_bytes = None
    try:
        body_bytes = await request.body()
        if body_bytes:
            content_type = request.headers.get(const.CONTENT_TYPE_HEADER, "")
            request_body = parse_request_body(body_bytes, content_type)
    except Exception:
        pass
    
    return request_body, body_bytes

async def read_and_parse_response_body(response: Response) -> Tuple[Optional[object], Optional[bytes]]:
    """Read and parse response body from response.
    
    Args:
        response: FastAPI Response object
        
    Returns:
        Tuple of (parsed_response_body, raw_body_bytes)
    """
    response_body = None
    body_bytes = None
    content_type = response.headers.get(const.CONTENT_TYPE_HEADER, "")
    
    if hasattr(response, 'body_iterator'):
        body = b""
        try:
            async for chunk in response.body_iterator:
                body += chunk
            
            if body:
                body_bytes = body
                response_body = parse_response_body(body, content_type)
        except Exception:
            pass
    
    return response_body, body_bytes

def log_incoming_request(
    method: str,
    path: str,
    client_ip: str,
    headers: Dict[str, str],
    query_params: Dict[str, str],
    body: Optional[object]
):
    """Log incoming request details.
    
    Args:
        method: HTTP method
        path: Request path
        client_ip: Client IP address
        headers: Request headers (will be filtered for sensitive data)
        query_params: Query parameters
        body: Parsed request body
    """
    filtered_headers = filter_sensitive_headers(headers)
    
    incoming_log_args = [
        "method", method,
        "path", path,
        "client-ip", client_ip,
        "headers", filtered_headers,
        "query_params", query_params,
        "body", body
    ]
    logger.Infow("Incoming request", *incoming_log_args)

def log_completed_request(response_body: Optional[object]):
    """Log completed request with response body.
    
    Args:
        response_body: Parsed response body
    """
    logger.Infow("Request completed", "response", response_body)

