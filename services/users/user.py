import re
from fastapi import Request, HTTPException, status
from sqlmodel import select
from server.logger import setup_logger
from server.middleware.middleware import get_body
from services.users.sql import User, encode_password
from common.models.sql import get_db_session
from common.components import get_component

logger = setup_logger(__name__)

def create_user(request: Request):
    """Create a new user in the database.
    
    Note: The users table must be created manually via DDL before starting the application.
    This function assumes the table already exists.
    """
    # Ensure database connection is initialized (lazy initialization)
    # This will trigger database connection creation if not already connected
    get_component("database")
    
    logger.Info("Creating user")
    body = get_body(request)
    
    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body is required"
        )
    
    try:
        # Get required fields
        name = body.get("name")
        email = body.get("email")
        password = body.get("password")
        
        if not name or not email or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="name, email, and password are required"
            )
        
        # Encode password to base64
        encoded_password = encode_password(password)
        
        # Create user using database session
        user_id = None
        try:
            with get_db_session() as session:
                # Check if user with email already exists
                statement = select(User).where(User.email == email)
                existing_user = session.exec(statement).first()
                if existing_user:
                    # Raise HTTPException before any commit
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="User with this email already exists"
                    )
                
                # Create new user
                user = User(
                    name=name,
                    email=email,
                    password=encoded_password,
                    phone=body.get("phone"),
                    address=body.get("address"),
                    is_active=body.get("is_active", True)
                )
                session.add(user)
                # Flush to get the ID without committing yet (sends to DB but doesn't commit)
                session.flush()
                # Refresh to ensure we have the ID loaded
                session.refresh(user)
                user_id = user.id
                # session.commit() is called automatically by get_db_session on successful exit
            
            logger.Infow("User created successfully", "email", email, "user_id", user_id)
            return {
                "message": "User created successfully",
                "user_id": user_id
            }
        except HTTPException as e:
            logger.Errorw("Failed to create user", "error", str(e))
            raise
        
    except HTTPException as e:
        logger.Errorw("Failed to create user", "error", str(e))
        raise
    except Exception as e:
        # Format error message to single line (remove newlines, tabs, extra spaces)
        error_msg = str(e)
        # Replace newlines and tabs with spaces, then collapse multiple spaces
        error_msg = re.sub(r'[\n\r\t]+', ' ', error_msg)
        error_msg = re.sub(r'\s+', ' ', error_msg).strip()
        
        logger.Errorw("Failed to create user", "error", error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {error_msg}"
        )

def get_all_users(request: Request):
    """Get all users from the database.
    
    Note: The users table must be created manually via DDL before starting the application.
    This function assumes the table already exists.
    """
    # Ensure database connection is initialized (lazy initialization)
    # This will trigger database connection creation if not already connected
    get_component("database")
    
    logger.Info("Getting all users")
    try:
        with get_db_session() as session:
            users = session.exec(select(User)).all()
            # Convert SQLModel objects to dictionaries for JSON serialization
            users_list = [user.model_dump() for user in users]
            return {"users": users_list}
    except Exception as e:
        # Format error message to single line (remove newlines, tabs, extra spaces)
        error_msg = str(e)
        # Replace newlines and tabs with spaces, then collapse multiple spaces
        error_msg = re.sub(r'[\n\r\t]+', ' ', error_msg)
        error_msg = re.sub(r'\s+', ' ', error_msg).strip()
        
        logger.Errorw("Failed to get all users", "error", error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get all users: {error_msg}"
        )