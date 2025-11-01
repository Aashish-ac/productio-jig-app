"""
Configuration settings for Camera Test Tool V2
"""
import os
from pathlib import Path
from dataclasses import dataclass

@dataclass
class Config:
    """Application configuration"""
    
    # Telnet Settings
    TELNET_USERNAME: str = "root"
    TELNET_PASSWORD: str = "root"
    TELNET_PORT: int = 23
    TELNET_TIMEOUT: int = 10
    TELNET_MAX_RETRIES: int = 3
    TELNET_RETRY_DELAY: int = 2
    
    # WebSocket Settings (deprecated - use TCP instead)
    WEBSOCKET_URL: str = "ws://localhost:8080"
    WEBSOCKET_TIMEOUT: int = 30
    WEBSOCKET_PING_INTERVAL: int = 20
    WEBSOCKET_READY_MESSAGE: str = "I am ready"
    
    # TCP Listener Settings (replaces WebSocket)
    TCP_HOST: str = "localhost"
    TCP_PORT: int = 8080
    TCP_TIMEOUT: int = 30
    TCP_RECONNECT_DELAY: int = 5
    TCP_MAX_RECONNECT_ATTEMPTS: int = 10
    TCP_READY_MESSAGE: str = "I am ready"
    
    # Database Settings
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "camera_test_db"
    DB_USER: str = "camera_test_user"
    DB_PASSWORD: str = "camera_test_pass"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    
    # Test Commands
    TEST_COMMANDS: dict = None
    
    # Application Directories
    BASE_DIR: Path = Path(__file__).parent.parent
    LOG_DIR: Path = BASE_DIR / "logs"
    DATA_DIR: Path = BASE_DIR / "data"
    
    def __post_init__(self):
        """Initialize configuration"""
        # Ensure directories exist
        self.LOG_DIR.mkdir(exist_ok=True)
        self.DATA_DIR.mkdir(exist_ok=True)
        
        # Initialize test commands
        if self.TEST_COMMANDS is None:
            self.TEST_COMMANDS = {
                'led_test': 'test_led',
                'irled_test': 'test_irled',
                'ircut_test': 'test_ircut',
                'speaker_test': 'test_speaker',
                'get_status': 'status',
                'reboot': 'reboot'
            }
    
    @classmethod
    def from_env(cls):
        """Create config from environment variables"""
        config = cls()
        
        # Override with environment variables if present
        config.TELNET_USERNAME = os.getenv('TELNET_USER', config.TELNET_USERNAME)
        config.TELNET_PASSWORD = os.getenv('TELNET_PASS', config.TELNET_PASSWORD)
        config.TELNET_PORT = int(os.getenv('TELNET_PORT', config.TELNET_PORT))
        
        config.WEBSOCKET_URL = os.getenv('WEBSOCKET_URL', config.WEBSOCKET_URL)
        
        config.DB_HOST = os.getenv('DB_HOST', config.DB_HOST)
        config.DB_PORT = int(os.getenv('DB_PORT', config.DB_PORT))
        config.DB_NAME = os.getenv('DB_NAME', config.DB_NAME)
        config.DB_USER = os.getenv('DB_USER', config.DB_USER)
        config.DB_PASSWORD = os.getenv('DB_PASSWORD', config.DB_PASSWORD)
        
        return config


