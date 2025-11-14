from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.requests import Request as StarletteRequest
from typing import Dict
import uuid
import json
from server.logger import set_request_id, get_request_id
from server.middleware.bodylogger import (
    read_and_parse_request_body,
    read_and_parse_response_body,
    log_incoming_request,
    log_completed_request
)
from common import constants as const

def _normalize_headers(headers) -> Dict[str, str]:
    """Normalize headers to lowercase and remove content-length header.
    
    Args:
        headers: Headers dictionary or Headers object
        
    Returns:
        Dictionary with lowercase header keys and content-length removed
    """
    normalized = {k.lower(): v for k, v in headers.items()}
    normalized.pop(const.CONTENT_LENGTH_HEADER, None)
    return normalized

def apply_middleware(app: FastAPI):
    """Apply all middleware to the FastAPI app.
    
    This function should be called from main.py after creating the app.
    All middleware setup logic is contained here.
    
    Note: Middleware executes in reverse order of registration.
    So we register logging first, then request_id, so execution order is:
    1. request_id middleware (sets request_id)
    2. logging middleware (can use request_id)
    """
    _add_request_logging_middleware(app)
    _add_request_id_middleware(app)

def _get_or_generate_request_id(request: Request) -> str:
    """Check request headers for request-id, if present use it, else generate new one.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        str: Request ID from headers or newly generated UUID
    """
    request_id = None
    for header_name in const.REQUEST_ID_HEADER_VARIANTS:
        request_id = request.headers.get(header_name)
        if request_id:
            break
    
    if not request_id:
        request_id = str(uuid.uuid4())
    
    return request_id

def _add_request_id_middleware(app):
    """Middleware to extract or generate a unique request ID for each request.
    
    Checks for Request-ID header (case-insensitive) and uses it if present,
    otherwise generates a new UUID. Automatically adds request_id to all JSON responses.
    """
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = _get_or_generate_request_id(request)
        
        set_request_id(request_id)
        
        response = await call_next(request)
        
        response.headers[const.REQUEST_ID_RESPONSE_HEADER] = request_id
        
        content_type = response.headers.get(const.CONTENT_TYPE_HEADER, "")
        if content_type.startswith(const.APPLICATION_JSON) and hasattr(response, 'body_iterator'):
            body = b""
            try:
                async for chunk in response.body_iterator:
                    body += chunk
                
                if body:
                    response_data = json.loads(body.decode("utf-8"))
                    if isinstance(response_data, dict):
                        response_data[const.REQUEST_ID_RESPONSE_KEY] = request_id
                        new_headers = _normalize_headers(response.headers)
                        return JSONResponse(
                            content=response_data,
                            status_code=response.status_code,
                            headers=new_headers
                        )
            except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
                if body:
                    new_headers = _normalize_headers(response.headers)
                    return Response(
                        content=body,
                        status_code=response.status_code,
                        headers=new_headers,
                        media_type=content_type
                    )
        
        return response

def _add_request_logging_middleware(app: FastAPI):
    """Middleware to log essential request details for each API call."""
    
    @app.middleware("http")
    async def log_request(request: Request, call_next):
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        should_log = path not in const.EXCLUDED_LOG_PATHS
        
        headers = dict(request.headers)
        query_params = dict(request.query_params) if request.query_params else {}
        
        request_body, body_bytes = await read_and_parse_request_body(request)
        
        request.state.body = request_body
        request.state.body_bytes = body_bytes
        object.__setattr__(request, 'body', request_body)
        
        if should_log:
            log_incoming_request(method, path, client_ip, headers, query_params, request_body)
        
        if body_bytes is not None:
            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request = StarletteRequest(request.scope, receive)
            object.__setattr__(request, 'body', request_body)
            request.state.body = request_body
            request.state.body_bytes = body_bytes
        
        response = await call_next(request)
        response_body, body_bytes = await read_and_parse_response_body(response)
        
        if body_bytes is not None:
            try:
                new_headers = _normalize_headers(response.headers)
                content_type = response.headers.get(const.CONTENT_TYPE_HEADER, "")
                response = Response(
                    content=body_bytes,
                    status_code=response.status_code,
                    headers=new_headers,
                    media_type=content_type
                )
            except Exception:
                pass
        
        if should_log:
            log_completed_request(response_body)
        
        return response

def get_current_request_id() -> str:
    """Dependency function to get the current request ID in route handlers.
    
    Usage:
        @router.get("/")
        def my_endpoint(request_id: str = Depends(get_current_request_id)):
            return {"request_id": request_id}
    """
    return get_request_id()

def get_request_body(request: Request):
    """Dependency function to get the parsed request body in route handlers.
    
    The body is already parsed by the middleware and stored in request.state.body.
    For JSON requests, it returns a dict. For other content types, it returns a string.
    
    Usage:
        @router.post("/")
        def my_endpoint(body = Depends(get_request_body)):
            return {"received": body}
    
    Or with type hints:
        @router.post("/")
        def my_endpoint(body: dict = Depends(get_request_body)):
            return {"received": body}
    """
    return getattr(request.state, 'body', None)

def get_body(request: Request):
    """Helper function to get parsed request body directly from request object.
    
    Tries request.body first (if set by middleware), falls back to request.state.body.
    
    Usage:
        @router.post("/")
        def my_endpoint(request: Request):
            body = get_body(request)
            return {"received": body}
    """
    body = request.__dict__.get('body', None)
    if body is not None and not callable(body):
        return body
    return getattr(request.state, 'body', None)