import base64
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from server.logger import setup_logger

logger = setup_logger(__name__)

class User(SQLModel, table=True):
    """
    User model for the users table.
    
    Table: users
    Database: testdb
    """
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True, description="User ID (auto-increment)")
    name: str = Field(max_length=255, description="User's full name")
    email: str = Field(unique=True, index=True, max_length=255, description="User's email address")
    password: str = Field(max_length=512, description="Base64 encoded password")
    created_at: datetime = Field(default_factory=datetime.now, description="Account creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update timestamp")
    is_active: bool = Field(default=True, description="Whether the user account is active")
    last_login: Optional[datetime] = Field(default=None, description="Last login timestamp")
    phone: Optional[str] = Field(default=None, max_length=20, description="User's phone number")
    address: Optional[str] = Field(default=None, max_length=500, description="User's address")

def encode_password(password: str) -> str:
    """
    Encode password to base64.
    
    Args:
        password: Plain text password
        
    Returns:
        Base64 encoded password string
        
    Example:
        encoded = encode_password("mypassword123")
    """
    return base64.b64encode(password.encode('utf-8')).decode('utf-8')


def decode_password(encoded_password: str) -> str:
    """
    Decode base64 encoded password.
    
    Args:
        encoded_password: Base64 encoded password
        
    Returns:
        Decoded password string
        
    Example:
        password = decode_password(encoded_password)
    """
    return base64.b64decode(encoded_password.encode('utf-8')).decode('utf-8')

