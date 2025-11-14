import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from server.logger import setup_logger

logger = setup_logger(__name__)

class Env:
    """Configuration struct (similar to Go's common.Env)."""
    
    def __init__(self):
        """Initialize with default values."""
        self.SERVER_HOST: str = "0.0.0.0"
        self.SERVER_PORT: int = 8080
        self.APP_NAME: str = "app"
        self.ENV: str = "dev1"
        self.DB_HOST: str = "localhost"
        self.DB_PORT: int = 3306
        self.DB_USER: str = "root"
        self.DB_PASSWORD: str = ""
        self.DB_NAME: str = "testdb"
    
    def update_from_dict(self, data: Dict[str, Any]):
        """Update config fields from a dictionary (from JSON unmarshaling)."""
        for key, value in data.items():
            attr_name = key.upper()
            if hasattr(self, attr_name):
                setattr(self, attr_name, value)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by key (case-insensitive, supports both JSON and Python naming)."""
        if hasattr(self, key):
            return getattr(self, key)
        key_upper = key.upper()
        if hasattr(self, key_upper):
            return getattr(self, key_upper)
        key_snake = key.upper().replace('-', '_')
        if hasattr(self, key_snake):
            return getattr(self, key_snake)
        return default
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        result = {}
        for key in dir(self):
            if not key.startswith('_') and not callable(getattr(self, key)):
                result[key] = getattr(self, key)
        return result

_env_instance = None

def _get_env():
    """Get or create the global Env instance."""
    global _env_instance
    if _env_instance is None:
        _env_instance = Env()
    return _env_instance

Env = _get_env()

def _try_read(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Try to read and parse a config file.
    Returns the config dict if successful, None if file doesn't exist, raises exception if file exists but fails to parse.
    
    Args:
        file_path: File name or path. If absolute path (starts with /), use as-is.
                   If relative, resolve relative to current working directory.
    """
    if file_path.startswith('/'):
        resolved_path = Path(file_path)
    else:
        resolved_path = Path.cwd() / file_path
    
    if not resolved_path.exists():
        return None
    
    try:
        with open(resolved_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, PermissionError) as e:
        raise e

def InitializeConfig(logger_instance=None):
    """
    Initialize configuration (similar to common.InitializeEnv in Go).
    Loads config from files and updates the global Env struct.
    
    Args:
        logger_instance: Optional logger instance. If not provided, uses module logger.
    """
    if logger_instance is None:
        logger_instance = logger
    
    config_files = ["/etc/config.json", "config.json"]
    
    for file_path in config_files:
        try:
            data = _try_read(file_path)
            if data is not None:
                Env.update_from_dict(data)
                logger_instance.Infow("Read configs from", "file", file_path)
                return
        except Exception as e:
            logger_instance.Errorw("Error reading config file", "error", str(e), "file", file_path)
    
    logger_instance.Error("Config file having issue. Please check the config file.")

Config = Env
