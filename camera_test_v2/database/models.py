"""
Database models for Camera Test Tool V2
Using SQLAlchemy async ORM
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Boolean
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class User(Base):
    """User table for authentication"""
    __tablename__ = "users"
    
    id = mapped_column(Integer, primary_key=True)
    employee_id = mapped_column(String(50), unique=True, nullable=False)
    name = mapped_column(String(100), nullable=False)
    password_hash = mapped_column(String(255), nullable=False)
    role = mapped_column(String(20), default="user")  # 'user' or 'admin'
    is_active = mapped_column(Boolean, default=True)
    created_at = mapped_column(DateTime, default=datetime.now)
    
    # Relationships
    test_results = relationship("TestResult", back_populates="user")
    
    def __repr__(self):
        return f"<User(employee_id='{self.employee_id}', name='{self.name}')>"


class Camera(Base):
    """Camera information table"""
    __tablename__ = "cameras"
    
    id = mapped_column(Integer, primary_key=True)
    serial_number = mapped_column(String(50), unique=True, nullable=False)
    ip_address = mapped_column(String(50), nullable=False)
    model = mapped_column(String(100))
    status = mapped_column(String(20), default="unknown")  # 'connected', 'disconnected', 'testing'
    last_seen = mapped_column(DateTime)
    created_at = mapped_column(DateTime, default=datetime.now)
    
    # Relationships
    test_results = relationship("TestResult", back_populates="camera")
    
    def __repr__(self):
        return f"<Camera(serial='{self.serial_number}', ip='{self.ip_address}')>"


class TestResult(Base):
    """Test results table"""
    __tablename__ = "test_results"
    
    id = mapped_column(Integer, primary_key=True)
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    camera_id = mapped_column(Integer, ForeignKey("cameras.id"), nullable=False)
    camera_serial = mapped_column(String(50), nullable=False)
    
    # Test results
    led_test = mapped_column(String(10), nullable=False)  # 'PASS', 'FAIL', 'NOT_TESTED'
    irled_test = mapped_column(String(10), nullable=False)
    ircut_test = mapped_column(String(10), nullable=False)
    speaker_test = mapped_column(String(10), nullable=False)
    
    # Status
    overall_status = mapped_column(String(10), nullable=False)  # 'PASS', 'FAIL'
    notes = mapped_column(Text)
    test_date = mapped_column(DateTime, default=datetime.now)
    
    # Relationships
    user = relationship("User", back_populates="test_results")
    camera = relationship("Camera", back_populates="test_results")
    
    def __repr__(self):
        return f"<TestResult(camera='{self.camera_serial}', status='{self.overall_status}')>"


class Database:
    """
    Database manager with async SQLAlchemy
    """
    
    def __init__(self, database_url: str = None, db_host: str = None, 
                 db_port: int = None, db_name: str = None, 
                 db_user: str = None, db_password: str = None,
                 pool_size: int = 10, max_overflow: int = 20):
        """
        Initialize database connection
        
        Args:
            database_url: Full PostgreSQL connection URL (optional)
            db_host, db_port, db_name, db_user, db_password: Individual params
            pool_size: Connection pool size
            max_overflow: Maximum overflow connections
        """
        # Build connection URL
        if database_url is None:
            database_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        self.engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            echo=False
        )
        
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info(f"Database initialized: {db_name}")
    
    async def create_tables(self):
        """Create all tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")
    
    async def get_session(self) -> AsyncSession:
        """Get async database session"""
        async with self.async_session() as session:
            yield session
    
    async def close(self):
        """Close database connection"""
        await self.engine.dispose()
        logger.info("Database connection closed")

