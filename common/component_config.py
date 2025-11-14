"""
Component Configuration Module

This module registers components based on JSON configuration.
Components are registered with their connection status (up/down) and host information.

JSON format:
{
    "mysql": [{"host": "127.0.0.1:3306", "status": "up"}],
    "redis": [{"host": "127.0.0.1:6379", "status": "up"}],
    "kafka": [{"host": "127.0.0.1:9092", "status": "down"}]
}
"""
import json
from typing import Dict, Any, List
from server.logger import setup_logger
from common.components import (
    register_component_factory,
    register_factory_registration_function,
    set_component_metadata
)
from common.models.sql import init_connection_pool, get_engine, close_connection_pool
from common.env import Config

logger = setup_logger(__name__)


def register_components_from_config(config: Dict[str, List[Dict[str, str]]]):
    """
    Register all components from JSON configuration.
    
    For each component in the config:
    - If status is "up", register the component factory
    - If status is "down", only store metadata (don't register factory)
    - Store metadata (host, status) for all components
    
    Args:
        config: Dictionary with component names as keys and lists of metadata as values
                Example: {
                    "mysql": [{"host": "127.0.0.1:3306", "status": "up"}],
                    "redis": [{"host": "127.0.0.1:6379", "status": "up"}],
                    "kafka": [{"host": "127.0.0.1:9092", "status": "down"}]
                }
    
    Example:
        from common.component_config import register_components_from_config
        
        config = {
            "mysql": [{"host": "127.0.0.1:3306", "status": "up"}],
            "redis": [{"host": "127.0.0.1:6379", "status": "up"}]
        }
        register_components_from_config(config)
    """
    for component_name, metadata_list in config.items():
        # Store metadata for this component
        set_component_metadata(component_name, metadata_list)
        
        # Check if any instance has status "up"
        has_up_status = any(item.get("status", "down").lower() == "up" for item in metadata_list)
        
        if not has_up_status:
            logger.Infow("Component has status 'down', skipping registration", "component", component_name)
            continue
        
        # Register factory registration function based on component type
        if component_name.lower() in ["mysql", "database", "db"]:
            _register_mysql_factory(metadata_list[0])
        else:
            logger.Warnw("Unknown component type, skipping", "component", component_name)


def _register_mysql_factory(metadata: Dict[str, str]):
    """Register MySQL database factory registration function."""
    host_port = metadata.get("host", "localhost:3306")
    host, port = _parse_host_port(host_port, default_port=3306)
    
    def register_mysql_factory():
        """Function that registers the MySQL factory (called on first access)."""
        def create_mysql():
            """Factory function to create MySQL connection on first access."""
            logger.Info("Creating MySQL database connection (lazy initialization)")
            
            # Update Config with host and port from metadata
            Config.DB_HOST = host
            Config.DB_PORT = port
            
            # Initialize connection pool
            init_connection_pool(
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=3600,
                pool_pre_ping=True
            )
            
            # Get engine and return it
            engine = get_engine()
            
            # Update metadata status to "up" after successful connection
            _update_component_status("mysql", host_port, "up")
            
            return engine
        
        register_component_factory(
            name="database",
            factory=create_mysql,
            cleanup_callback=close_connection_pool
        )
    
    register_factory_registration_function("database", register_mysql_factory)
    logger.Infow("MySQL factory registration function registered", "host", host_port)

def _parse_host_port(host_port: str, default_port: int) -> tuple:
    """Parse host:port string into host and port."""
    if ":" in host_port:
        host, port_str = host_port.rsplit(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            port = default_port
    else:
        host = host_port
        port = default_port
    return host, port


def _update_component_status(component_name: str, host: str, status: str):
    """Update status of a component in metadata."""
    from common.components import get_component_metadata, set_component_metadata
    
    metadata = get_component_metadata()
    if component_name in metadata:
        for item in metadata[component_name]:
            if item.get("host") == host:
                item["status"] = status
        set_component_metadata(component_name, metadata[component_name])


def register_all_factory_registration_functions():
    """
    Register all factory registration functions from config.json.
    
    This function reads component configuration from config.json and registers
    components based on their status (up/down).
    
    Deprecated: Use register_components_from_config() directly with your config.
    """
    # Try to read from config.json
    try:
        from common.env import InitializeConfig
        InitializeConfig()
        
        # Check if components config exists in Config
        if hasattr(Config, 'COMPONENTS'):
            components_config = getattr(Config, 'COMPONENTS')
            if isinstance(components_config, dict):
                register_components_from_config(components_config)
                return
        
        # Fallback: Use default MySQL registration
        logger.Info("No COMPONENTS config found, using default MySQL registration")
        register_components_from_config({
            "mysql": [{"host": f"{Config.DB_HOST}:{Config.DB_PORT}", "status": "up"}]
        })
    except Exception as e:
        logger.Errorw("Failed to register components from config", "error", str(e))
        # Fallback to default MySQL
        register_components_from_config({
            "mysql": [{"host": "localhost:3306", "status": "up"}]
        })
