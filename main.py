from fastapi import FastAPI
from server.middleware.middleware import apply_middleware
from common.env import InitializeConfig, Config
from server.logger import setup_logger
from server import server
from server.controller_register import register_all_routers

def main():
    logger = setup_logger(__name__)
    InitializeConfig(logger)
    app = FastAPI(lifespan=server.lifespan)
    register_all_routers(app)
    apply_middleware(app)
    return app

app = main()

if __name__ == "__main__":
    server.start_server(app, Config)