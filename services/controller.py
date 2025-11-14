from fastapi import APIRouter
from server.logger import setup_logger
from common.env import Config

router = APIRouter()
logger = setup_logger(__name__)

@router.get("/")
def hello_world():
    logger.Info("Hello World")
    a = Config.APP_NAME
    return {
        "message": "Hello World"
    }