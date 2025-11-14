from fastapi import APIRouter, Request
from server.logger import setup_logger
from server.middleware.middleware import get_body
from common import constants as const

router = APIRouter()
logger = setup_logger(__name__)

@router.get("/")
def hello_world():
    logger.Info("Hello World")
    return {
        "message": "Hello World"
    }

@router.get("/test/config")
def test_config(request: Request):
    headers = dict(request.headers)
    content_type = headers.get(const.CONTENT_TYPE_HEADER, "")
    api_key = headers.get(const.API_KEY_HEADER, "")
    body = get_body(request)
    
    logger.Infow("Test Config", "content-type", content_type, "api-key", api_key, "body", body)
    return {
        "message": "Test Config",
        "headers": {
            "content-type": content_type,
            "api-key": api_key
        }
    }