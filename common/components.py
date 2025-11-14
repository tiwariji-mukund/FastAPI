"""
Component Registry Module

Similar to Spring Boot's ApplicationContext, this module provides:
- Component registration at application startup
- Dependency injection for registered components
- Lifecycle management (initialization and cleanup)

Components can be:
- Database connections
- Third-party service clients (Redis, Elasticsearch, etc.)
- Any service that needs to be initialized once and reused
"""
from typing import Dict, Any, Optional, Callable
from contextlib import asynccontextmanager
from server.logger import setup_logger

logger = setup_logger(__name__)

# Global component registry
_component_registry: Dict[str, Any] = {}
_component_factories: Dict[str, Callable] = {}  # Factory functions for lazy initialization
_factory_registration_functions: Dict[str, Callable] = {}  # Functions that register factories (called on first access)
_cleanup_callbacks: Dict[str, Callable] = {}
_component_metadata: Dict[str, list] = {}  # Component metadata: {"component_name": [{"host": "...", "status": "up/down"}, ...]}


def register_component_factory(
    name: str,
    factory: Callable,
    cleanup_callback: Optional[Callable] = None
):
    """
    Register a component factory for lazy initialization.
    
    Components are only created when first accessed, not at application startup.
    Similar to Spring Boot's @Lazy annotation.
    
    Args:
        name: Unique name for the component (e.g., "database", "redis", "elasticsearch")
        factory: Factory function that creates and returns the component instance
        cleanup_callback: Optional callback function to cleanup the component on shutdown
    
    Example:
        from common.components import register_component_factory
        
        # Register database factory (will be created on first access)
        def create_database():
            from common.models.sql import init_connection_pool, get_engine
            init_connection_pool()
            return get_engine()
        
        register_component_factory(
            "database",
            create_database,
            cleanup_callback=lambda: close_connection_pool()
        )
    """
    if name in _component_factories:
        logger.Warnw("Component factory already registered, overwriting", "component", name)
    
    _component_factories[name] = factory
    
    if cleanup_callback:
        _cleanup_callbacks[name] = cleanup_callback
    
    logger.Infow("Component factory registered", "component", name)


def register_factory_registration_function(name: str, registration_func: Callable):
    """
    Register a function that will register the component factory on first access.
    
    This allows factories to be registered lazily - only when a service first tries to use them.
    No logging is done here to keep startup silent.
    
    Args:
        name: Unique name for the component
        registration_func: Function that registers the component factory (called on first access)
    
    Example:
        from common.components import register_factory_registration_function
        
        def register_database_factory():
            # This function registers the database factory
            register_component_factory("database", create_database)
        
        register_factory_registration_function("database", register_database_factory)
    """
    _factory_registration_functions[name] = registration_func
    # No logging - keep startup silent


def register_component(
    name: str,
    component: Any,
    cleanup_callback: Optional[Callable] = None
):
    """
    Register a component instance directly (for already-initialized components).
    
    Args:
        name: Unique name for the component
        component: The component instance to register
        cleanup_callback: Optional callback function to cleanup the component on shutdown
    """
    if name in _component_registry:
        logger.Warnw("Component already registered, overwriting", "component", name)
    
    _component_registry[name] = component
    
    if cleanup_callback:
        _cleanup_callbacks[name] = cleanup_callback
    
    logger.Infow("Component registered", "component", name)


def get_component(name: str) -> Any:
    """
    Get a registered component by name (lazy initialization).
    
    If component is not yet created, it will be created on first access.
    If factory is not yet registered, it will be registered first, then component created.
    Subsequent calls return the cached instance.
    
    Similar to Spring Boot's @Autowired or dependency injection with lazy loading.
    
    Args:
        name: Name of the component to retrieve
        
    Returns:
        The registered component instance (created on first access)
        
    Raises:
        KeyError: If component factory registration function is not registered
        
    Example:
        from common.components import get_component
        
        # Get database engine (factory registered and component created on first access)
        engine = get_component("database")
        
        # Get Redis client (factory registered and component created on first access)
        redis_client = get_component("redis")
    """
    # If component already exists, return it
    if name in _component_registry:
        return _component_registry[name]
    
    # If factory exists, create component lazily
    if name in _component_factories:
        logger.Infow("Lazy initializing component", "component", name)
        try:
            factory = _component_factories[name]
            component = factory()
            _component_registry[name] = component
            logger.Infow("Component initialized", "component", name)
            return component
        except Exception as e:
            logger.Errorw("Failed to initialize component", "component", name, "error", str(e))
            raise
    
    # If factory registration function exists, register factory first, then create component
    if name in _factory_registration_functions:
        logger.Infow("Lazy registering factory for component", "component", name)
        try:
            registration_func = _factory_registration_functions[name]
            registration_func()  # This registers the factory
            # Now factory should be registered, create component
            if name in _component_factories:
                factory = _component_factories[name]
                component = factory()
                _component_registry[name] = component
                logger.Infow("Component initialized", "component", name)
                return component
            else:
                raise RuntimeError(f"Factory registration function for '{name}' did not register the factory")
        except Exception as e:
            logger.Errorw("Failed to register factory for component", "component", name, "error", str(e))
            raise
    
    # Component not found
    available = list(_factory_registration_functions.keys()) + list(_component_factories.keys()) + list(_component_registry.keys())
    raise KeyError(
        f"Component '{name}' is not registered. "
        f"Available components: {available}"
    )


def has_component(name: str) -> bool:
    """
    Check if a component is registered (either as instance, factory, or registration function).
    
    Args:
        name: Name of the component to check
        
    Returns:
        True if component is registered (as instance, factory, or registration function), False otherwise
    """
    return name in _component_registry or name in _component_factories or name in _factory_registration_functions


def get_all_components() -> Dict[str, Any]:
    """
    Get all initialized components.
    
    Returns:
        Dictionary of all initialized components
    """
    return _component_registry.copy()


def get_available_factories() -> list:
    """
    Get list of component factory names that are registered but not yet initialized.
    
    Returns:
        List of component names that have factories but haven't been created yet
    """
    initialized = set(_component_registry.keys())
    factories = set(_component_factories.keys())
    return list(factories - initialized)


def get_available_registration_functions() -> list:
    """
    Get list of component names that have registration functions but factories not yet registered.
    
    Returns:
        List of component names that have registration functions but factories not yet registered
    """
    registered_factories = set(_component_factories.keys())
    registration_funcs = set(_factory_registration_functions.keys())
    return list(registration_funcs - registered_factories)


def set_component_metadata(component_name: str, metadata: list):
    """
    Set metadata for a component (host, status, etc.).
    
    Args:
        component_name: Name of the component (e.g., "mysql", "redis", "kafka")
        metadata: List of metadata objects, each with "host" and "status" keys
                  Example: [{"host": "127.0.0.1:3306", "status": "up"}]
    """
    _component_metadata[component_name] = metadata


def get_component_metadata() -> Dict[str, list]:
    """
    Get all component metadata.
    
    Returns:
        Dictionary mapping component names to their metadata lists
        Example: {
            "mysql": [{"host": "127.0.0.1:3306", "status": "up"}],
            "redis": [{"host": "127.0.0.1:6379", "status": "up"}]
        }
    """
    return _component_metadata.copy()


def cleanup_all_components():
    """
    Cleanup all components that have cleanup callbacks.
    
    This should be called at application shutdown.
    
    Example:
        from common.components import cleanup_all_components
        cleanup_all_components()
    """
    logger.Info("Cleaning up all registered components")
    
    for name, callback in _cleanup_callbacks.items():
        try:
            logger.Infow("Cleaning up component", "component", name)
            callback()
            logger.Infow("Component cleaned up", "component", name)
        except Exception as e:
            logger.Errorw("Failed to cleanup component", "component", name, "error", str(e))


def clear_registry():
    """
    Clear all registered components (mainly for testing).
    
    Example:
        from common.components import clear_registry
        clear_registry()
    """
    _component_registry.clear()
    _component_factories.clear()
    _factory_registration_functions.clear()
    _cleanup_callbacks.clear()
    _component_metadata.clear()
    logger.Info("Component registry cleared")


# FastAPI Dependency Injection Helpers

def get_database():
    """
    FastAPI dependency to get database engine.
    
    Usage:
        from fastapi import Depends
        from common.components import get_database
        
        @router.get("/users")
        def get_users(db = Depends(get_database)):
            # Use db for database operations
            pass
    """
    return get_component("database")


def get_redis():
    """
    FastAPI dependency to get Redis client.
    
    Usage:
        from fastapi import Depends
        from common.components import get_redis
        
        @router.get("/cache")
        def get_cache(redis = Depends(get_redis)):
            # Use redis for cache operations
            pass
    """
    return get_component("redis")

