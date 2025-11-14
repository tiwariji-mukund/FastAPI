from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse, Response
import uuid
import json
from server.logger import set_request_id, get_request_id

def apply_middleware(app: FastAPI):
    """Apply all middleware to the FastAPI app.
    
    This function should be called from main.py after creating the app.
    All middleware setup logic is contained here.
    """
    _add_request_id_middleware(app)

def _add_request_id_middleware(app):
    """Middleware to extract or generate a unique request ID for each request.
    
    Checks for Request-ID header (case-insensitive) and uses it if present,
    otherwise generates a new UUID. Automatically adds request_id to all JSON responses.
    """
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = (
            request.headers.get("request-id") or 
            request.headers.get("Request-ID") or 
            request.headers.get("X-Request-ID") or
            request.headers.get("x-request-id")
        )
        
        if not request_id:
            request_id = str(uuid.uuid4())
        
        set_request_id(request_id)
        
        response = await call_next(request)
        
        response.headers["X-Request-ID"] = request_id
        
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("application/json") and hasattr(response, 'body_iterator'):
            body = b""
            try:
                async for chunk in response.body_iterator:
                    body += chunk
                
                if body:
                    response_data = json.loads(body.decode("utf-8"))
                    if isinstance(response_data, dict):
                        response_data["request_id"] = request_id
                        new_headers = dict(response.headers)
                        new_headers.pop("content-length", None)
                        new_headers.pop("Content-Length", None)
                        return JSONResponse(
                            content=response_data,
                            status_code=response.status_code,
                            headers=new_headers
                        )
            except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
                if body:
                    new_headers = dict(response.headers)
                    new_headers.pop("content-length", None)
                    new_headers.pop("Content-Length", None)
                    return Response(
                        content=body,
                        status_code=response.status_code,
                        headers=new_headers,
                        media_type=content_type
                    )
        
        return response

def get_current_request_id() -> str:
    """Dependency function to get the current request ID in route handlers.
    
    Usage:
        @router.get("/")
        def my_endpoint(request_id: str = Depends(get_current_request_id)):
            return {"request_id": request_id}
    """
    return get_request_id()