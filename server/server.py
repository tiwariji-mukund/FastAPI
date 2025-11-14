import uvicorn
from fastapi import FastAPI

def start_server(app: FastAPI, config):
    """
    Start the FastAPI server with the given configuration.
    
    Args:
        app: FastAPI application instance
        config: Configuration object (Env instance) containing SERVER_HOST and SERVER_PORT
    """
    host = config.SERVER_HOST
    port = config.SERVER_PORT
    uvicorn.run(app, host=host, port=port)

def stop_server(app: FastAPI):
    uvicorn.shutdown()