"""
TCP listener for PCB ready status monitoring
Replaces WebSocket with raw TCP for simpler, lower-overhead communication
"""
import asyncio
import logging
from typing import Optional, Callable
from datetime import datetime
from .config import Config

logger = logging.getLogger(__name__)


class TCPListener:
    """
    Manages raw TCP connection for receiving PCB ready status
    Listens for "I am ready" messages over plain TCP
    """
    
    def __init__(self, host: str = None, port: int = None):
        """
        Initialize TCP listener
        
        Args:
            host: TCP server host (default from config)
            port: TCP server port (default from config)
        """
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.is_connected: bool = False
        self.is_listening: bool = False
        self.listen_task: Optional[asyncio.Task] = None
        self.reconnect_task: Optional[asyncio.Task] = None
        self._callbacks: list[Callable] = []
        
        config = Config()
        
        # Parse host and port from config or use provided values
        if host and port:
            self.host = host
            self.port = port
        else:
            # Extract from config URL (format: ws://host:port or host:port)
            tcp_config = getattr(config, 'TCP_HOST', None), getattr(config, 'TCP_PORT', None)
            if tcp_config[0] and tcp_config[1]:
                self.host = tcp_config[0]
                self.port = tcp_config[1]
            else:
                # Fallback: parse from WEBSOCKET_URL (backward compatibility)
                ws_url = config.WEBSOCKET_URL.replace('ws://', '').replace('wss://', '')
                if ':' in ws_url:
                    self.host, port_str = ws_url.split(':', 1)
                    self.port = int(port_str)
                else:
                    self.host = ws_url
                    self.port = 8080  # Default port
        
        self.timeout = getattr(config, 'TCP_TIMEOUT', 30)
        self.reconnect_delay = getattr(config, 'TCP_RECONNECT_DELAY', 5)
        self.ready_message = getattr(config, 'TCP_READY_MESSAGE', config.WEBSOCKET_READY_MESSAGE)
        self.max_reconnect_attempts = getattr(config, 'TCP_MAX_RECONNECT_ATTEMPTS', 10)
        self.reconnect_attempts = 0
        
    def register_callback(self, callback: Callable):
        """Register callback for 'I am ready' messages"""
        self._callbacks.append(callback)
    
    async def connect(self) -> bool:
        """
        Connect to TCP server
        
        Returns:
            True if connected successfully
        """
        try:
            logger.info(f"Connecting to TCP server: {self.host}:{self.port}")
            
            # Create TCP connection with timeout
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=10
            )
            
            self.is_connected = True
            self.reconnect_attempts = 0  # Reset on successful connection
            logger.info(f"✓ TCP connection established: {self.host}:{self.port}")
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"TCP connection timeout: {self.host}:{self.port}")
            self.is_connected = False
            return False
        except ConnectionRefusedError:
            logger.error(f"TCP connection refused: {self.host}:{self.port}")
            self.is_connected = False
            return False
        except Exception as e:
            logger.error(f"TCP connection error: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from TCP server"""
        self.is_listening = False
        
        # Cancel listening task
        if self.listen_task:
            self.listen_task.cancel()
            try:
                await self.listen_task
            except asyncio.CancelledError:
                pass
        
        # Cancel reconnect task
        if self.reconnect_task:
            self.reconnect_task.cancel()
            try:
                await self.reconnect_task
            except asyncio.CancelledError:
                pass
        
        # Close connection
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                logger.warning(f"TCP close error: {e}")
        
        self.reader = None
        self.writer = None
        self.is_connected = False
        logger.info("TCP connection closed")
    
    async def start_listening(self, auto_reconnect: bool = True):
        """
        Start listening for 'I am ready' messages
        
        Args:
            auto_reconnect: If True, automatically reconnect on connection loss
        """
        if not self.is_connected:
            logger.error("Cannot start listening: not connected")
            if auto_reconnect:
                await self._start_auto_reconnect()
            return
        
        self.is_listening = True
        self.listen_task = asyncio.create_task(self._listen_loop(auto_reconnect))
    
    async def _listen_loop(self, auto_reconnect: bool = True):
        """Internal listening loop"""
        logger.info("TCP listener started")
        buffer = b""  # Buffer for partial messages
        
        while self.is_listening:
            try:
                if not self.is_connected or not self.reader:
                    if auto_reconnect:
                        logger.info("Connection lost, waiting for reconnect...")
                        await asyncio.sleep(1)
                        continue
                    else:
                        break
                
                # Read data with timeout
                try:
                    data = await asyncio.wait_for(
                        self.reader.read(1024),  # Read up to 1KB at a time
                        timeout=self.timeout
                    )
                except asyncio.TimeoutError:
                    # Timeout is normal, just continue listening
                    logger.debug("TCP receive timeout (expected)")
                    continue
                
                if not data:
                    # EOF - connection closed
                    logger.warning("TCP connection closed by remote")
                    self.is_connected = False
                    
                    if auto_reconnect:
                        await self._start_auto_reconnect()
                    break
                
                # Add to buffer and process complete lines
                buffer += data
                
                # Process complete messages (assuming newline-terminated)
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    message = line.decode('utf-8', errors='ignore').strip()
                    
                    logger.debug(f"TCP message received: {message}")
                    
                    # Check if this is the ready message
                    if self.ready_message.lower() in message.lower():
                        logger.info(f"✓ PCB Ready status received: {message}")
                        await self._trigger_callbacks(message)
                
                # Also check if message is exactly "I am ready" (no newline needed)
                if buffer and self.ready_message.lower() in buffer.decode('utf-8', errors='ignore').lower():
                    message = buffer.decode('utf-8', errors='ignore').strip()
                    logger.info(f"✓ PCB Ready status received: {message}")
                    await self._trigger_callbacks(message)
                    buffer = b""  # Clear buffer after processing
                
            except asyncio.CancelledError:
                logger.info("TCP listener cancelled")
                break
            except ConnectionResetError:
                logger.warning("TCP connection reset by remote")
                self.is_connected = False
                if auto_reconnect:
                    await self._start_auto_reconnect()
                break
            except Exception as e:
                logger.error(f"TCP listening error: {e}")
                await asyncio.sleep(1)
        
        logger.info("TCP listener stopped")
    
    async def _start_auto_reconnect(self):
        """Start automatic reconnection"""
        if self.reconnect_task and not self.reconnect_task.done():
            return  # Already reconnecting
        
        self.reconnect_task = asyncio.create_task(self._auto_reconnect_loop())
    
    async def _auto_reconnect_loop(self):
        """Automatic reconnection loop"""
        logger.info("Starting automatic reconnection...")
        
        while not self.is_connected and self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                self.reconnect_attempts += 1
                logger.info(f"Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}")
                
                if await self.connect():
                    # Reconnected successfully, restart listening
                    if self.is_listening:
                        self.listen_task = asyncio.create_task(self._listen_loop(auto_reconnect=True))
                    break
                else:
                    await asyncio.sleep(self.reconnect_delay)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reconnection error: {e}")
                await asyncio.sleep(self.reconnect_delay)
        
        if not self.is_connected:
            logger.error(f"Failed to reconnect after {self.max_reconnect_attempts} attempts")
    
    async def _trigger_callbacks(self, message: str):
        """Trigger all registered callbacks with the message"""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message, datetime.now())
                else:
                    callback(message, datetime.now())
            except Exception as e:
                logger.error(f"TCP callback error: {e}")
    
    async def send_message(self, message: str):
        """
        Send message to TCP server
        
        Args:
            message: Message to send
        """
        if not self.is_connected or not self.writer:
            logger.error("Cannot send message: not connected")
            return
        
        try:
            # Ensure message ends with newline
            if not message.endswith('\n'):
                message += '\n'
            
            self.writer.write(message.encode('utf-8'))
            await self.writer.drain()
            logger.debug(f"TCP message sent: {message.strip()}")
        except Exception as e:
            logger.error(f"TCP send error: {e}")
            self.is_connected = False


async def on_pcb_ready(message: str, timestamp: datetime):
    """
    Example callback function for PCB ready status
    
    Args:
        message: The ready message
        timestamp: When the message was received
    """
    print(f"[{timestamp}] PCB is ready: {message}")

