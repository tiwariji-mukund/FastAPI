from fastapi import APIRouter
from server.logger import setup_logger
from common.env import Config

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

