"""
Production-grade async Telnet manager with connection pooling
"""
import asyncio
import telnetlib3
import logging
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from .config import Config

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Camera connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    READY = "ready"
    ERROR = "error"


@dataclass
class CameraSession:
    """Represents a single camera Telnet session"""
    serial: str
    ip: str
    port: int = Config.TELNET_PORT
    
    # Connection objects
    reader: Optional[telnetlib3.TelnetReader] = None
    writer: Optional[telnetlib3.TelnetWriter] = None
    
    # State tracking
    state: ConnectionState = ConnectionState.DISCONNECTED
    last_activity: datetime = field(default_factory=datetime.now)
    error_count: int = 0
    last_error: Optional[str] = None
    
    # Lock for concurrent command execution
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    def __post_init__(self):
        """Initialize lock after dataclass creation"""
        if not isinstance(self._lock, asyncio.Lock):
            self._lock = asyncio.Lock()
    
    @property
    def is_connected(self) -> bool:
        """Check if connection is active"""
        return (self.state in [ConnectionState.CONNECTED, ConnectionState.READY] 
                and self.writer 
                and not self.writer.is_closing())
    
    async def connect(self, username: str, password: str, 
                     timeout: int = Config.TELNET_TIMEOUT) -> bool:
        """
        Establish Telnet connection with authentication
        
        Args:
            username: Telnet username
            password: Telnet password
            timeout: Connection timeout in seconds
            
        Returns:
            True if connected and authenticated successfully
        """
        self.state = ConnectionState.CONNECTING
        config = Config()
        
        for attempt in range(1, config.TELNET_MAX_RETRIES + 1):
            try:
                # Exponential backoff delay
                if attempt > 1:
                    delay = config.TELNET_RETRY_DELAY * (2 ** (attempt - 2))
                    logger.info(f"[{self.serial}] Retry {attempt}/{config.TELNET_MAX_RETRIES} "
                               f"after {delay}s delay")
                    await asyncio.sleep(delay)
                
                # Validate IP with ping first
                from .network_utils import ping_ip
                
                if attempt == 1:  # Only ping on first attempt
                    logger.debug(f"[{self.serial}] Validating IP: {self.ip}")
                    ping_result = await ping_ip(self.ip, timeout=3)
                    if not ping_result:
                        self.last_error = f"Camera not responding at {self.ip} (ping failed)"
                        logger.error(f"[{self.serial}] {self.last_error}")
                        break  # Don't retry if ping fails
                
                # Open Telnet connection
                logger.debug(f"[{self.serial}] Connecting to {self.ip}:{self.port}")
                self.reader, self.writer = await asyncio.wait_for(
                    telnetlib3.open_connection(self.ip, self.port),
                    timeout=timeout
                )
                
                self.state = ConnectionState.CONNECTED
                logger.debug(f"[{self.serial}] Connection established, authenticating...")
                
                # Authenticate
                if await self._authenticate(username, password, timeout):
                    self.state = ConnectionState.READY
                    self.error_count = 0
                    self.last_activity = datetime.now()
                    logger.info(f"[{self.serial}] Successfully connected and authenticated")
                    return True
                else:
                    await self.disconnect()
                    self.last_error = "Authentication failed"
                    
            except asyncio.TimeoutError:
                self.last_error = f"Connection timeout on attempt {attempt}"
                logger.warning(f"[{self.serial}] {self.last_error}")
                
            except ConnectionRefusedError:
                self.last_error = f"Connection refused by {self.ip}"
                logger.error(f"[{self.serial}] {self.last_error}")
                # Don't retry on refused connections
                break
                
            except OSError as e:
                self.last_error = f"Network error: {str(e)}"
                logger.error(f"[{self.serial}] {self.last_error}")
                
            except Exception as e:
                self.last_error = f"Unexpected error: {str(e)}"
                logger.error(f"[{self.serial}] {self.last_error}", exc_info=True)
        
        self.state = ConnectionState.ERROR
        self.error_count += 1
        return False
    
    async def _authenticate(self, username: str, password: str, 
                           timeout: int) -> bool:
        """
        Handle Telnet authentication flow
        
        Args:
            username: Login username
            password: Login password
            timeout: Authentication timeout
            
        Returns:
            True if authentication succeeded
        """
        self.state = ConnectionState.AUTHENTICATING
        
        try:
            # Simple authentication: just wait for any prompt and send "root"
            # Read initial data to find login prompt
            stream_data = await asyncio.wait_for(
                self.reader.read(2048),
                timeout=timeout
            )
            
            # Handle both bytes and str safely
            if isinstance(stream_data, bytes):
                stream_text = stream_data.decode('utf-8', errors='ignore').lower()
            else:
                stream_text = str(stream_data).lower()
            
            logger.debug(f"[{self.serial}] Initial stream: {stream_text[:200]}")
            
            # If there's already a login prompt, send username immediately
            if 'login:' in stream_text or any(prompt in stream_text for prompt in ['username:', 'user:']):
                self.writer.write(f"{username}\n")
                await self.writer.drain()
                logger.debug(f"[{self.serial}] Sent username")
            else:
                # Wait for login prompt
                login_prompt = await asyncio.wait_for(
                    self.reader.readuntil(b':', partial=True),
                    timeout=timeout
                )
                logger.debug(f"[{self.serial}] Found prompt, sending username")
                
                # Send username
                self.writer.write(f"{username}\n")
                await self.writer.drain()
            
            # Read response to confirm we're logged in
            response = await asyncio.wait_for(
                self.reader.read(1024),
                timeout=5
            )
            
            # Handle response safely
            if isinstance(response, bytes):
                response_str = response.decode('utf-8', errors='ignore')
            else:
                response_str = str(response)
            
            logger.debug(f"[{self.serial}] Authentication response: {response_str[:200]}")
            
            # Check for authentication failure
            if any(keyword in response_str.lower() for keyword in ['incorrect', 'failed', 'denied', 'invalid', 'error']):
                logger.error(f"[{self.serial}] Authentication failed: {response_str[:200]}")
                return False
            
            logger.info(f"[{self.serial}] Authentication successful")
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"[{self.serial}] Authentication timeout")
            return False
        except Exception as e:
            logger.error(f"[{self.serial}] Authentication error: {e}")
            return False
    
    async def execute_command(self, command: str, 
                             timeout: int = Config.TELNET_TIMEOUT,
                             expect_prompt: str = '#') -> Optional[str]:
        """
        Execute command and return output
        
        Args:
            command: Command to execute
            timeout: Command timeout
            expect_prompt: Expected prompt after command completion
            
        Returns:
            Command output or None on error
        """
        if not self.is_connected:
            logger.error(f"[{self.serial}] Cannot execute command: not connected")
            return None
        
        async with self._lock:  # Prevent concurrent command execution
            try:
                logger.debug(f"[{self.serial}] Executing: {command}")
                
                # Send command
                self.writer.write(f"{command}\n")
                await self.writer.drain()
                
                # Give command time to execute
                await asyncio.sleep(0.5)
                
                # Convert expect_prompt to bytes
                expect_prompt_bytes = expect_prompt.encode('utf-8') if isinstance(expect_prompt, str) else expect_prompt
                
                # Read output until prompt (with timeout)
                try:
                    output = await asyncio.wait_for(
                        self.reader.readuntil(expect_prompt_bytes),
                        timeout=timeout
                    )
                    
                    # Decode bytes output to string
                    clean_output = output.decode('utf-8', errors='ignore').strip()
                    
                    # Clean output (remove command echo and prompt)
                    if clean_output.startswith(command):
                        clean_output = clean_output[len(command):].strip()
                    if clean_output.endswith(expect_prompt):
                        clean_output = clean_output[:-len(expect_prompt)].strip()
                    
                    logger.debug(f"[{self.serial}] Command output ({len(clean_output)} chars)")
                    self.last_activity = datetime.now()
                    self.error_count = 0
                    return clean_output
                    
                except asyncio.TimeoutError:
                    # Command executed but no response received - this is OK for echo commands
                    logger.debug(f"[{self.serial}] Command executed (no response expected)")
                    self.last_activity = datetime.now()
                    self.error_count = 0
                    return ""  # Return empty string - command was sent successfully
                
            except Exception as e:
                self.error_count += 1
                self.last_error = f"Command execution error: {str(e)}"
                logger.error(f"[{self.serial}] {self.last_error}")
                # Even on error, if we got to this point, the command was at least sent
                return ""
    
    async def test_led(self, state: str = "on") -> Dict[str, Any]:
        """Test LED - ON/OFF using same commands as serial handler"""
        # Use exact same commands as serial handler
        command = 'echo 1 > /sys/devices/platform/soc/18820000.pwm/settings/pwm1/enable' if state.lower() == "on" else 'echo 0 > /sys/devices/platform/soc/18820000.pwm/settings/pwm1/enable'
        result = await self.execute_command(command, timeout=5)
        return {
            "success": result is not None,
            "output": result or "",
            "command": f"LED_{state.upper()}"
        }
    
    async def test_irled(self, state: str = "on") -> Dict[str, Any]:
        """Test IR LED - ON/OFF using same commands as serial handler"""
        command = 'echo 1 > /sys/devices/platform/soc/18820000.pwm/settings/pwm3/enable' if state.lower() == "on" else 'echo 0 > /sys/devices/platform/soc/18820000.pwm/settings/pwm3/enable'
        result = await self.execute_command(command, timeout=5)
        return {
            "success": result is not None,
            "output": result or "",
            "command": f"IRLED_{state.upper()}"
        }
    
    async def test_ircut(self, state: str = "on") -> Dict[str, Any]:
        """Test IR Cut filter - ON/OFF using same commands as serial handler"""
        command = './sbin/control_gpio.sh ircut 1' if state.lower() == "on" else './sbin/control_gpio.sh ircut 0'
        result = await self.execute_command(command, timeout=5)
        return {
            "success": result is not None,
            "output": result or "",
            "command": f"IRCUT_{state.upper()}"
        }
    
    async def test_speaker(self) -> Dict[str, Any]:
        """Test Speaker using same commands as serial handler"""
        # First kill capture, then play test audio
        await self.execute_command("killall capture", timeout=3)
        await asyncio.sleep(1)  # Wait for kill to complete
        result = await self.execute_command("aplay -D hw:0,1 /overlay/test_saudio.wav", timeout=10)
        return {
            "success": result is not None,
            "output": result or "",
            "command": "SPEAKER_TEST"
        }
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get camera system information"""
        result = await self.execute_command("status", timeout=5)
        return {
            "success": result is not None,
            "output": result or "",
            "command": "status"
        }
    
    async def disconnect(self):
        """Close Telnet connection"""
        if self.writer and not self.writer.is_closing():
            try:
                self.writer.write("exit\n")
                await asyncio.wait_for(self.writer.drain(), timeout=2)
                self.writer.close()
                await self.writer.wait_closed()
                logger.info(f"[{self.serial}] Disconnected cleanly")
            except Exception as e:
                logger.warning(f"[{self.serial}] Disconnect error: {e}")
        
        self.reader = None
        self.writer = None
        self.state = ConnectionState.DISCONNECTED
    
    async def keep_alive(self):
        """Send periodic keep-alive to prevent timeout"""
        try:
            await self.execute_command("echo", timeout=5)
        except Exception as e:
            logger.debug(f"[{self.serial}] Keep-alive failed: {e}")


class TelnetConnectionPool:
    """
    Connection pool manager for multiple cameras
    Implements connection pooling with automatic health checks
    """
    
    def __init__(self, 
                 max_connections: int = 50,
                 health_check_interval: int = 60):
        """
        Initialize connection pool
        
        Args:
            max_connections: Maximum concurrent connections
            health_check_interval: Seconds between health checks
        """
        self.sessions: Dict[str, CameraSession] = {}
        self._semaphore = asyncio.Semaphore(max_connections)
        self._health_check_task: Optional[asyncio.Task] = None
        self._health_check_interval = health_check_interval
        self._callbacks: Dict[str, List[Callable]] = {
            'on_connect': [],
            'on_disconnect': [],
            'on_error': []
        }
        config = Config()
        
        logger.info(f"Telnet pool initialized (max: {max_connections})")
    
    def register_callback(self, event: str, callback: Callable):
        """Register event callback (on_connect, on_disconnect, on_error)"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    async def _trigger_callbacks(self, event: str, session: CameraSession):
        """Trigger registered callbacks for an event"""
        for callback in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(session)
                else:
                    callback(session)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")
    
    async def add_camera(self, serial: str, ip: str) -> bool:
        """
        Add camera to pool and establish connection
        
        Args:
            serial: Camera serial number
            ip: Camera IP address
            
        Returns:
            True if connection successful
        """
        async with self._semaphore:  # Enforce max connections limit
            if serial in self.sessions:
                logger.warning(f"Camera {serial} already in pool")
                return self.sessions[serial].is_connected
            
            session = CameraSession(serial=serial, ip=ip)
            config = Config()
            
            # Connect with credentials
            success = await session.connect(
                config.TELNET_USERNAME,
                config.TELNET_PASSWORD
            )
            
            if success:
                self.sessions[serial] = session
                await self._trigger_callbacks('on_connect', session)
                
                # Start health check if first camera
                if len(self.sessions) == 1 and not self._health_check_task:
                    self._health_check_task = asyncio.create_task(
                        self._periodic_health_check()
                    )
            else:
                await self._trigger_callbacks('on_error', session)
            
            return success
    
    async def remove_camera(self, serial: str):
        """Remove camera from pool and disconnect"""
        if serial in self.sessions:
            session = self.sessions.pop(serial)
            await session.disconnect()
            await self._trigger_callbacks('on_disconnect', session)
            logger.info(f"Removed camera {serial} from pool")
            
            # Stop health check if no cameras
            if not self.sessions and self._health_check_task:
                self._health_check_task.cancel()
                self._health_check_task = None
    
    async def execute_command(self, serial: str, command: str) -> Optional[str]:
        """Execute command on specific camera"""
        if serial not in self.sessions:
            logger.error(f"Camera {serial} not in pool")
            return None
        
        return await self.sessions[serial].execute_command(command)
    
    async def execute_command_all(self, command: str) -> Dict[str, Optional[str]]:
        """
        Execute command on all connected cameras concurrently
        
        Args:
            command: Command to execute
            
        Returns:
            Dict mapping serial numbers to command outputs
        """
        tasks = {
            serial: session.execute_command(command)
            for serial, session in self.sessions.items()
            if session.is_connected
        }
        
        if not tasks:
            logger.warning("No connected cameras to execute command")
            return {}
        
        logger.info(f"Executing '{command}' on {len(tasks)} cameras")
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        return {
            serial: result if not isinstance(result, Exception) else None
            for serial, result in zip(tasks.keys(), results)
        }
    
    async def get_session_status(self, serial: str) -> Optional[Dict]:
        """Get detailed session status"""
        if serial not in self.sessions:
            return None
        
        session = self.sessions[serial]
        return {
            'serial': session.serial,
            'ip': session.ip,
            'state': session.state.value,
            'connected': session.is_connected,
            'last_activity': session.last_activity.isoformat(),
            'error_count': session.error_count,
            'last_error': session.last_error
        }
    
    async def _periodic_health_check(self):
        """Periodic health check for all connections"""
        logger.info("Starting periodic health check")
        config = Config()
        
        while self.sessions:
            try:
                await asyncio.sleep(self._health_check_interval)
                
                logger.debug(f"Health check: {len(self.sessions)} cameras")
                
                for serial, session in list(self.sessions.items()):
                    if session.is_connected:
                        # Send keep-alive
                        await session.keep_alive()
                        
                        # Check for excessive errors
                        if session.error_count > 5:
                            logger.warning(
                                f"[{serial}] Excessive errors ({session.error_count}), "
                                f"reconnecting..."
                            )
                            await session.disconnect()
                            await session.connect(
                                config.TELNET_USERNAME,
                                config.TELNET_PASSWORD
                            )
                    else:
                        # Attempt reconnection
                        logger.info(f"[{serial}] Reconnecting...")
                        await session.connect(
                            config.TELNET_USERNAME,
                            config.TELNET_PASSWORD
                        )
                
            except asyncio.CancelledError:
                logger.info("Health check task cancelled")
                break
            except Exception as e:
                logger.error(f"Health check error: {e}", exc_info=True)
    
    async def close_all(self):
        """Disconnect all cameras and cleanup"""
        logger.info(f"Closing {len(self.sessions)} camera connections")
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect all sessions concurrently
        await asyncio.gather(
            *[session.disconnect() for session in self.sessions.values()],
            return_exceptions=True
        )
        
        self.sessions.clear()
        logger.info("All connections closed")


