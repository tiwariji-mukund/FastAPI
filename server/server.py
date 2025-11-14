import logging
import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from server.logger import setup_logger
from common.env import Config

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for FastAPI application startup and shutdown."""
    logger = setup_logger(__name__)
    actual_port = int(os.environ.get("PORT", os.environ.get("UVICORN_PORT", Config.SERVER_PORT)))
    logger.Infow("Server running on port", "port", actual_port, "configured_port", Config.SERVER_PORT)
    yield
    logger.Infow("Server shutting down")

def start_server(app: FastAPI, config, reload: bool = False):
    """
    Start the FastAPI server with the given configuration.
    
    Args:
        app: FastAPI application instance
        config: Configuration object (Env instance) containing SERVER_HOST and SERVER_PORT
        reload: Whether to enable auto-reload on file changes (default: False)
    """
    logger = setup_logger(__name__)
    host = config.SERVER_HOST
    port = config.SERVER_PORT
    logger.Info("Server running on port %s", port)
    uvicorn.run(app, host=host, port=port, reload=reload, log_config=None)

def stop_server(app: FastAPI):
    logger = setup_logger(__name__)
    logger.Infow("Stopping server")
    uvicorn.shutdown()