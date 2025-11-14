"""
MySQL Database Connection Module

This module provides MySQL database connection pooling and session management.
Other services can use this module to:
- Get database connection from pool
- Get database sessions for their operations
- Connection pool automatically manages connections with timeout

Table creation logic should be handled by respective services according to their use cases.
"""
from typing import Optional
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlmodel import Session
from contextlib import contextmanager
from server.logger import setup_logger
from common.env import Config

logger = setup_logger(__name__)

# Global variables for database connection pool
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_database_url() -> str:
    """
    Construct MySQL database URL from configuration.
    
    Reads database configuration from Config object:
    - DB_HOST: Database host (default: localhost)
    - DB_PORT: Database port (default: 3306)
    - DB_USER: Database username (default: root)
    - DB_PASSWORD: Database password (default: empty)
    - DB_NAME: Database name (default: fastapi_db)
    
    Returns:
        str: MySQL connection URL in format: mysql+pymysql://user:password@host:port/dbname
    """
    db_host = getattr(Config, 'DB_HOST', 'localhost')
    db_port = getattr(Config, 'DB_PORT', 3306)
    db_user = getattr(Config, 'DB_USER', 'root')
    db_password = getattr(Config, 'DB_PASSWORD', '')
    db_name = getattr(Config, 'DB_NAME', 'fastapi_db')
    
    # Construct MySQL URL
    # Using pymysql as the MySQL driver
    database_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    return database_url


def init_connection_pool(
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_timeout: int = 30,
    pool_recycle: int = 3600,
    pool_pre_ping: bool = True
):
    """
    Initialize database connection pool.
    
    Creates a connection pool that manages database connections efficiently.
    Connections are reused from the pool, and new connections are created
    only when needed. Connections are automatically recycled after timeout.
    
    Args:
        pool_size: Number of connections to maintain in the pool (default: 5)
        max_overflow: Maximum number of connections to create beyond pool_size (default: 10)
        pool_timeout: Seconds to wait before giving up on getting a connection (default: 30)
        pool_recycle: Seconds after which a connection is recycled (default: 3600 = 1 hour)
        pool_pre_ping: If True, verify connections before using (default: True)
    
    Example:
        from common.models.sql import init_connection_pool
        
        # Initialize with default settings
        init_connection_pool()
        
        # Or with custom settings
        init_connection_pool(pool_size=10, pool_timeout=60)
    """
    global _engine, _SessionLocal
    
    try:
        database_url = get_database_url()
        db_host = getattr(Config, 'DB_HOST', 'localhost')
        db_name = getattr(Config, 'DB_NAME', 'fastapi_db')
        
        logger.Infow(
            "Initializing database connection pool",
            "host", db_host,
            "database", db_name,
            "pool_size", pool_size,
            "max_overflow", max_overflow,
            "pool_timeout", pool_timeout
        )
        
        # Create engine with connection pool settings
        _engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=pool_pre_ping,
            echo=False  # Set to True for SQL query logging
        )
        
        # Create session factory with SQLModel Session class
        # This ensures sessions have the exec() method for SQLModel queries
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine, class_=Session)
        
        logger.Info("Database connection pool initialized successfully")
        
    except Exception as e:
        logger.Errorw("Failed to initialize database connection pool", "error", str(e))
        raise


def get_engine() -> Engine:
    """
    Get the database engine instance with connection pool.
    
    Returns:
        Engine: SQLAlchemy engine instance with connection pool
        
    Raises:
        RuntimeError: If connection pool is not initialized
        
    Example:
        from common.models.sql import get_engine
        engine = get_engine()
    """
    if _engine is None:
        raise RuntimeError(
            "Database connection pool not initialized. "
            "Call init_connection_pool() first."
        )
    return _engine


def get_session() -> Session:
    """
    Get a new database session from the connection pool.
    
    The session is created from the connection pool. If no connections are available
    in the pool, a new connection will be created (up to max_overflow limit).
    If pool_timeout is reached, an exception will be raised.
    
    Note: Remember to close the session when done to return it to the pool.
    
    Returns:
        Session: SQLAlchemy session instance from connection pool
        
    Raises:
        RuntimeError: If connection pool is not initialized
        
    Example:
        from common.models.sql import get_session
        
        session = get_session()
        try:
            # Use session for database operations
            users = session.query(User).all()
        finally:
            session.close()  # Return connection to pool
    """
    if _SessionLocal is None:
        raise RuntimeError(
            "Database connection pool not initialized. "
            "Call init_connection_pool() first."
        )
    return _SessionLocal()


@contextmanager
def get_db_session():
    """
    Context manager for database session (auto-close on exit, returns connection to pool).
    
    Automatically handles:
    - Session commit on success
    - Session rollback on error
    - Session close (returns connection to pool)
    
    Yields:
        Session: Database session that will be automatically closed and returned to pool
        
    Example:
        from common.models.sql import get_db_session
        from my_service.models import User
        
        with get_db_session() as session:
            user = User(name="John", email="john@example.com")
            session.add(user)
            # session.commit() is called automatically on success
            # session.rollback() is called automatically on error
            # session.close() is called automatically (returns connection to pool)
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()  # Return connection to pool


def close_connection_pool():
    """
    Close database connection pool and cleanup all connections.
    
    This should be called during application shutdown to properly
    close all database connections.
    
    Example:
        from common.models.sql import close_connection_pool
        close_connection_pool()
    """
    global _engine, _SessionLocal
    
    if _engine:
        _engine.dispose()  # Close all connections in the pool
        logger.Info("Database connection pool closed")
    
    _engine = None
    _SessionLocal = None
