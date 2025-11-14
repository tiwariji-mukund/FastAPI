from fastapi import APIRouter, FastAPI
from typing import List, Tuple
from server.logger import setup_logger
from services import controller
from services.common import common

logger = setup_logger(__name__)

_registered_routers: List[Tuple[APIRouter, str]] = []

def register_router(router: APIRouter, service_name: str):
    """Register a router for a service.
    
    Args:
        router: The APIRouter instance to register
        service_name: Name of the service (e.g., "controller", "common")
    """
    if router not in [r[0] for r in _registered_routers]:
        _registered_routers.append((router, service_name))

def get_all_routers() -> List[Tuple[APIRouter, str]]:
    """Get all registered routers with their service names."""
    return _registered_routers.copy()

def register_all_routers(app: FastAPI):
    """Register all routers with the FastAPI app and log all routes."""
    for router, service_name in _registered_routers:
        app.include_router(router)
    
    log_all_routes(app)

def log_all_routes(app: FastAPI):
    """Log all registered routes, one per line."""
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = ', '.join(sorted(route.methods))
            path = route.path
            routes.append(f"{methods} {path}")
    
    for route_str in sorted(routes):
        logger.Info(f"Registered route: {route_str}")

register_router(controller.router, "controller")
register_router(common.router, "common")

