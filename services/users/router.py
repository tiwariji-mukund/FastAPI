from fastapi import APIRouter, Request
from server.logger import setup_logger
from services.users.user import create_user

router = APIRouter()
logger = setup_logger(__name__)

@router.post("/users/create")
def create_user_route(request: Request):
    logger.Info("Creating user route")
    return create_user(request)
