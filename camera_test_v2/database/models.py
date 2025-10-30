"""
Database models for Camera Test Tool V2
Using SQLAlchemy synchronous ORM (better for desktop apps)
"""
from sqlalchemy import create_engine, String, Integer, DateTime, Text, ForeignKey, Boolean, select, and_, or_, desc
from sqlalchemy.orm import DeclarativeBase, mapped_column, relationship, sessionmaker, Session
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
import bcrypt

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
    admin_id = mapped_column(Integer, nullable=True)  # Admin who created this user
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
    # --- Future-proof fields ---
    last_known_stage = mapped_column(String(10), nullable=True)
    last_known_serial = mapped_column(String(50), nullable=True)
    last_tested_by = mapped_column(Integer, nullable=True)  # FK to User.id or just employee_id
    last_tested_at = mapped_column(DateTime, nullable=True)
    
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
    # --- Future-proof fields ---
    test_stage = mapped_column(String(10), nullable=True)  # 'T1', 'L1', 'L2' etc
    camera_stage_before_test = mapped_column(String(10), nullable=True)
    camera_stage_after_test = mapped_column(String(10), nullable=True)
    serial_confirmed = mapped_column(Boolean, nullable=True)  # True if camera S/N matched against DB
    serial_received_from_camera = mapped_column(String(50), nullable=True)
    stage_confirmed_by_tool = mapped_column(Boolean, nullable=True)  # Did tool confirm stage before test?
    
    # Relationships
    user = relationship("User", back_populates="test_results")
    camera = relationship("Camera", back_populates="test_results")
    
    def __repr__(self):
        return f"<TestResult(camera='{self.camera_serial}', status='{self.overall_status}')>"


class Database:
    """
    Database manager with synchronous SQLAlchemy (better for desktop apps)
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
        # Build connection URL - using psycopg2 (synchronous driver)
        if database_url is None:
            database_url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
        self.engine = create_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            echo=False
        )
        
        self.Session = sessionmaker(
            bind=self.engine,
            expire_on_commit=False
        )
        
        logger.info(f"Database initialized: {db_name}")
    
    def initialize(self):
        """Initialize database - create tables synchronously"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        self.engine.dispose()
        logger.info("Database connection closed")
    
    # ===== USER MANAGEMENT METHODS =====
    
    def create_user(self, employee_id: str, name: str, password: str, 
                   role: str = "user", admin_id: Optional[int] = None) -> Optional[User]:
        """Create a new user with hashed password (synchronous)"""
        try:
            with self.Session() as session:
                # Check if user already exists
                result = session.execute(
                    select(User).where(User.employee_id == employee_id)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    logger.warning(f"User {employee_id} already exists")
                    return None
                
                # Hash password
                password_hash = bcrypt.hashpw(
                    password.encode('utf-8'), 
                    bcrypt.gensalt()
                ).decode('utf-8')
                
                # Create user
                new_user = User(
                    employee_id=employee_id,
                    name=name,
                    password_hash=password_hash,
                    role=role,
                    admin_id=admin_id,
                    is_active=True
                )
                session.add(new_user)
                session.commit()
                session.refresh(new_user)
                
                logger.info(f"Created user: {employee_id}")
                return new_user
        except Exception as e:
            logger.error(f"Error creating user: {e}", exc_info=True)
            return None
    
    def get_user_by_id(self, employee_id: str) -> Optional[User]:
        """Get user by employee ID (synchronous)"""
        try:
            with self.Session() as session:
                result = session.execute(
                    select(User).where(User.employee_id == employee_id)
                )
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None
    
    def get_user_by_db_id(self, user_db_id: int) -> Optional[User]:
        """Get user by primary key ID (synchronous)"""
        try:
            with self.Session() as session:
                return session.get(User, user_db_id)
        except Exception as e:
            logger.error(f"Error getting user by db id: {e}")
            return None

    def get_all_users(self, admin_id: Optional[int] = None) -> List[User]:
        """Get all users, optionally filtered by admin_id (synchronous)"""
        try:
            with self.Session() as session:
                query = select(User)
                if admin_id:
                    query = query.where(User.admin_id == admin_id)
                result = session.execute(query)
                return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    def update_user(self, employee_id: str, name: Optional[str] = None,
                   password: Optional[str] = None, is_active: Optional[bool] = None) -> bool:
        """Update user information (synchronous)"""
        try:
            with self.Session() as session:
                result = session.execute(
                    select(User).where(User.employee_id == employee_id)
                )
                user = result.scalar_one_or_none()
                if not user:
                    return False
                
                if name:
                    user.name = name
                if password:
                    user.password_hash = bcrypt.hashpw(
                        password.encode('utf-8'), 
                        bcrypt.gensalt()
                    ).decode('utf-8')
                if is_active is not None:
                    user.is_active = is_active
                
                session.commit()
                logger.info(f"Updated user: {employee_id}")
                return True
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False
    
    def delete_user(self, employee_id: str) -> bool:
        """Delete user (soft delete by setting is_active=False) (synchronous)"""
        return self.update_user(employee_id, is_active=False)
    
    def authenticate_user(self, employee_id: str, name: str,
                          provided_password: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Authenticate user - returns dict (synchronous method)
        
        For Users: Password is automatically employee_id + name
        For Admins: Password must be provided and verified
        
        Args:
            employee_id: Employee ID
            name: Full name
            provided_password: Password for admin login (optional for users)
            
        Returns:
            User data dict if authenticated, None otherwise
        """
        with self.Session() as session:
            try:
                result = session.execute(
                    select(User).where(User.employee_id == employee_id)
                )
                
                user = result.scalar_one_or_none()
                
                if not user:
                    logger.warning(f"User not found: {employee_id}")
                    return None
                    
                if not user.is_active:
                    logger.warning(f"User inactive: {employee_id}")
                    return None
                
                # For users: password is employee_id + name
                # For admins: use provided_password
                if user.role == "user":
                    password = employee_id + name
                elif user.role == "admin":
                    if not provided_password:
                        logger.warning(f"Admin login requires password")
                        return None
                    password = provided_password
                else:
                    logger.warning(f"Unknown role: {user.role}")
                    return None
                
                # Verify password
                if bcrypt.checkpw(
                    password.encode('utf-8'),
                    user.password_hash.encode('utf-8')
                ):
                    # Verify name matches
                    if user.name.strip().lower() != name.strip().lower():
                        logger.warning(f"Name mismatch for {employee_id}")
                        return None
                        
                    logger.info(f"User authenticated: {employee_id} ({user.role})")
                    
                    # Return dict - no session issues with sync
                    return {
                        'id': user.id,
                        'employee_id': user.employee_id,
                        'name': user.name,
                        'role': user.role,
                        'is_active': user.is_active,
                        'admin_id': user.admin_id,
                        'created_at': user.created_at
                    }
                else:
                    logger.warning(f"Password mismatch for {employee_id}")
                    return None
                    
            except Exception as e:
                logger.error(f"Authentication error: {e}", exc_info=True)
                return None
    
    def generate_next_employee_id(self, prefix: str = "USR") -> str:
        """Generate next available employee ID (e.g., USR001, USR002) (synchronous)"""
        try:
            with self.Session() as session:
                # Get all employee IDs with this prefix
                result = session.execute(
                    select(User.employee_id).where(
                        User.employee_id.like(f"{prefix}%")
                    )
                )
                existing_ids = [row[0] for row in result.all()]
                
                # Find next available number
                numbers = []
                for eid in existing_ids:
                    try:
                        # Extract number part (e.g., "001" from "USR001")
                        num_part = eid[len(prefix):]
                        numbers.append(int(num_part))
                    except ValueError:
                        continue
                
                # Find next number
                next_num = 1
                if numbers:
                    next_num = max(numbers) + 1
                
                # Format with leading zeros (3 digits)
                return f"{prefix}{next_num:03d}"
                
        except Exception as e:
            logger.error(f"Error generating employee ID: {e}")
            # Fallback: use timestamp
            import time
            return f"{prefix}{int(time.time()) % 10000:04d}"
    
    # ===== TEST RESULTS METHODS =====
    
    def get_test_results(self, user_id: Optional[int] = None,
                        camera_serial: Optional[str] = None,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None,
                        status: Optional[str] = None,
                        limit: int = 1000) -> List[TestResult]:
        """Get test results with optional filters (synchronous)"""
        try:
            with self.Session() as session:
                query = select(TestResult)
                
                conditions = []
                if user_id:
                    conditions.append(TestResult.user_id == user_id)
                if camera_serial:
                    conditions.append(TestResult.camera_serial == camera_serial)
                if start_date:
                    conditions.append(TestResult.test_date >= start_date)
                if end_date:
                    conditions.append(TestResult.test_date <= end_date)
                if status:
                    conditions.append(TestResult.overall_status == status)
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                query = query.order_by(desc(TestResult.test_date)).limit(limit)
                
                result = session.execute(query)
                return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting test results: {e}")
            return []
    
    def get_test_results_by_admin(self, admin_id: int,
                                  start_date: Optional[datetime] = None,
                                  end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get test results for all users created by an admin (synchronous)"""
        try:
            with self.Session() as session:
                # Get all users created by this admin
                users_result = session.execute(
                    select(User.id, User.name, User.employee_id).where(
                        User.admin_id == admin_id
                    )
                )
                user_ids = [row[0] for row in users_result.all()]
                
                if not user_ids:
                    return []
                
                # Get test results for these users
                query = select(TestResult, User.name, User.employee_id).join(
                    User, TestResult.user_id == User.id
                ).where(TestResult.user_id.in_(user_ids))
                
                if start_date:
                    query = query.where(TestResult.test_date >= start_date)
                if end_date:
                    query = query.where(TestResult.test_date <= end_date)
                
                query = query.order_by(desc(TestResult.test_date)).limit(1000)
                
                result = session.execute(query)
                results = []
                for test_result, user_name, employee_id in result.all():
                    results.append({
                        'id': test_result.id,
                        'user_name': user_name,
                        'employee_id': employee_id,
                        'camera_serial': test_result.camera_serial,
                        'led_test': test_result.led_test,
                        'irled_test': test_result.irled_test,
                        'ircut_test': test_result.ircut_test,
                        'speaker_test': test_result.speaker_test,
                        'overall_status': test_result.overall_status,
                        'test_date': test_result.test_date,
                        'notes': test_result.notes
                    })
                return results
        except Exception as e:
            logger.error(f"Error getting test results by admin: {e}")
            return []
    
    def create_test_result(self, user_id: int, camera_serial: str, camera_id: Optional[int] = None,
                          led_test: str = "NOT_TESTED", irled_test: str = "NOT_TESTED",
                          ircut_test: str = "NOT_TESTED", speaker_test: str = "NOT_TESTED",
                          overall_status: str = "PASS", notes: Optional[str] = None) -> Optional[TestResult]:
        """
        Create a new test result record (synchronous)
        
        Args:
            user_id: User database ID who performed the test
            camera_serial: Camera serial number
            camera_id: Camera database ID (optional, will lookup if not provided)
            led_test: LED test result ('PASS', 'FAIL', 'NOT_TESTED')
            irled_test: IR LED test result
            ircut_test: IR Cut test result
            speaker_test: Speaker test result
            overall_status: Overall test status ('PASS', 'FAIL')
            notes: Optional notes
            
        Returns:
            Created TestResult object or None on error
        """
        try:
            with self.Session() as session:
                # Get or create camera record
                if not camera_id:
                    result = session.execute(
                        select(Camera).where(Camera.serial_number == camera_serial)
                    )
                    camera = result.scalar_one_or_none()
                    
                    if not camera:
                        # Create camera record
                        camera = Camera(
                            serial_number=camera_serial,
                            ip_address=""  # Will be updated when camera connects
                        )
                        session.add(camera)
                        session.flush()  # Get camera.id
                    
                    camera_id = camera.id
                
                # Create test result
                test_result = TestResult(
                    user_id=user_id,
                    camera_id=camera_id,
                    camera_serial=camera_serial,
                    led_test=led_test,
                    irled_test=irled_test,
                    ircut_test=ircut_test,
                    speaker_test=speaker_test,
                    overall_status=overall_status,
                    notes=notes or "",
                    test_date=datetime.now()
                )
                
                session.add(test_result)
                session.commit()
                session.refresh(test_result)
                
                logger.info(f"Created test result for camera {camera_serial}")
                return test_result
                
        except Exception as e:
            logger.error(f"Error creating test result: {e}", exc_info=True)
            return None

