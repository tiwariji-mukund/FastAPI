#!/usr/bin/env python3
"""Run script that reads port from config and starts uvicorn server."""
import sys
import uvicorn
from common.env import InitializeConfig, Config
from server.logger import setup_logger

def run():
    """Run the FastAPI application using uvicorn with config from config.json.
    
    Port and host are automatically read from config.json.
    
    Usage:
        python run.py
        python run.py --log-level warning
        python run.py --log-level info --reload
    """
    logger = setup_logger(__name__)
    InitializeConfig(logger)
    
    host = Config.SERVER_HOST
    port = Config.SERVER_PORT
    
    log_level = "warning"
    reload = False
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ["--reload", "-r"]:
            reload = True
        elif arg == "--log-level" and i + 1 < len(args):
            log_level = args[i + 1]
            i += 1
        i += 1
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=reload
    )

if __name__ == "__main__":
    run()

