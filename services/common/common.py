from fastapi import APIRouter
from server.logger import setup_logger
from common.env import Config
from common import components

router = APIRouter()
logger = setup_logger(__name__)

@router.get("/config")
def get_config():
    """Get all configuration values. Logs them in terminal and returns as response."""
    from common import env as env_module
    config_obj = env_module.Config
    
    config_dict = config_obj.to_dict()
    config_str = {k: str(v) for k, v in config_dict.items()}
    
    kv_pairs = []
    for k, v in config_str.items():
        kv_pairs.extend([k, v])
    
    logger.Infow("logged config values", *kv_pairs)
    
    return {
        "msg": "logged config values"
    }

@router.get("/health")
def check_health():
    """
    Health check endpoint that lists all registered components.
    
    Returns information about:
    - Components that have been initialized (created on first access)
    - Component factories available for lazy initialization (not yet created)
    
    Similar to Spring Boot's actuator health endpoint.
    
    Returns:
        dict: Component metadata with host and status for each component
    """
    from common.components import get_component_metadata
    from server.middleware.middleware import get_current_request_id
    component_metadata = get_component_metadata()
    response = component_metadata.copy()
    return response