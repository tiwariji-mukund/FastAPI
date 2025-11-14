from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.requests import Request as StarletteRequest
from typing import Dict
import uuid
import json
from server.logger import set_request_id, get_request_id, setup_logger
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

def _add_request_id_middleware(app):
    """Middleware to extract or generate a unique request ID for each request.
    
    Checks for Request-ID header (case-insensitive) and uses it if present,
    otherwise generates a new UUID. Automatically adds request_id to all JSON responses.
    """
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = None
        for header_name in const.REQUEST_ID_HEADER_VARIANTS:
            request_id = request.headers.get(header_name)
            if request_id:
                break
        
        if not request_id:
            request_id = str(uuid.uuid4())
        
        set_request_id(request_id)
        
        response = await call_next(request)
        
        response.headers[const.REQUEST_ID_RESPONSE_HEADER] = request_id
        
        content_type = response.headers.get(const.CONTENT_LENGTH_HEADER, "")
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
    logger = setup_logger(__name__)
    
    @app.middleware("http")
    async def log_request(request: Request, call_next):
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        
        headers = dict(request.headers)
        filtered_headers = {k: v if k.lower() not in const.SENSITIVE_HEADERS else '***' for k, v in headers.items()}
        
        query_params = dict(request.query_params) if request.query_params else {}
        
        request_body = None
        body_bytes = None
        try:
            body_bytes = await request.body()
            if body_bytes:
                content_type = request.headers.get(const.CONTENT_TYPE_HEADER, "")
                if const.APPLICATION_JSON in content_type:
                    try:
                        request_body = json.loads(body_bytes.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        request_body = body_bytes.decode("utf-8", errors="replace")[:500]
                else:
                    request_body = body_bytes.decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        
        incoming_log_args = [
            "method", method,
            "path", path,
            "client-ip", client_ip,
            "headers", filtered_headers,
            "query_params", query_params,
            "body", request_body
        ]
        
        logger.Infow("Incoming request", *incoming_log_args)
        
        if body_bytes is not None:
            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request = StarletteRequest(request.scope, receive)
        
        response = await call_next(request)
        
        response_body = None
        content_type = response.headers.get(const.CONTENT_TYPE_HEADER, "")
        if hasattr(response, 'body_iterator'):
            body = b""
            try:
                async for chunk in response.body_iterator:
                    body += chunk
                
                if body:
                    if const.APPLICATION_JSON in content_type:
                        try:
                            response_body = json.loads(body.decode("utf-8"))
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            response_body = body.decode("utf-8", errors="replace")[:500]
                    else:
                        response_body = body.decode("utf-8", errors="replace")[:500]
                    
                    new_headers = _normalize_headers(response.headers)
                    response = Response(
                        content=body,
                        status_code=response.status_code,
                        headers=new_headers,
                        media_type=content_type
                    )
            except Exception:
                pass
        
        logger.Infow("Request completed", "response", response_body)
        
        return response

def get_current_request_id() -> str:
    """Dependency function to get the current request ID in route handlers.
    
    Usage:
        @router.get("/")
        def my_endpoint(request_id: str = Depends(get_current_request_id)):
            return {"request_id": request_id}
    """
    return get_request_id()