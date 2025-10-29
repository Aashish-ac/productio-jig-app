"""
WebSocket manager for PCB ready status monitoring
"""
import asyncio
import websockets
import logging
from typing import Optional, Callable
from datetime import datetime
from .config import Config

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connection for receiving PCB ready status
    """
    
    def __init__(self):
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected: bool = False
        self.is_listening: bool = False
        self.listen_task: Optional[asyncio.Task] = None
        self._callbacks: list[Callable] = []
        config = Config()
        self.url = config.WEBSOCKET_URL
        self.timeout = config.WEBSOCKET_TIMEOUT
        self.ping_interval = config.WEBSOCKET_PING_INTERVAL
        self.ready_message = config.WEBSOCKET_READY_MESSAGE
        
    def register_callback(self, callback: Callable):
        """Register callback for 'I am ready' messages"""
        self._callbacks.append(callback)
    
    async def connect(self) -> bool:
        """
        Connect to WebSocket server
        
        Returns:
            True if connected successfully
        """
        try:
            logger.info(f"Connecting to WebSocket server: {self.url}")
            self.websocket = await websockets.connect(
                self.url,
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_interval * 2,
                close_timeout=10
            )
            self.is_connected = True
            logger.info("WebSocket connected successfully")
            return True
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket server"""
        self.is_listening = False
        
        if self.listen_task:
            self.listen_task.cancel()
            try:
                await self.listen_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"WebSocket close error: {e}")
        
        self.websocket = None
        self.is_connected = False
        logger.info("WebSocket disconnected")
    
    async def start_listening(self):
        """
        Start listening for 'I am ready' messages
        Continuously monitors for PCB ready status
        """
        if not self.is_connected:
            logger.error("Cannot start listening: not connected")
            return
        
        self.is_listening = True
        self.listen_task = asyncio.create_task(self._listen_loop())
    
    async def _listen_loop(self):
        """Internal listening loop"""
        logger.info("WebSocket listener started")
        
        while self.is_listening and self.is_connected:
            try:
                # Wait for message with timeout
                message = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=self.timeout
                )
                
                logger.debug(f"WebSocket message received: {message}")
                
                # Check if this is the ready message
                if self.ready_message in message:
                    logger.info("PCB Ready status received!")
                    await self._trigger_callbacks(message)
                
            except asyncio.TimeoutError:
                # Timeout is normal, just continue
                logger.debug("WebSocket receive timeout (expected)")
                continue
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                self.is_connected = False
                break
                
            except Exception as e:
                logger.error(f"WebSocket listening error: {e}")
                await asyncio.sleep(1)
        
        logger.info("WebSocket listener stopped")
    
    async def _trigger_callbacks(self, message: str):
        """Trigger all registered callbacks with the message"""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message, datetime.now())
                else:
                    callback(message, datetime.now())
            except Exception as e:
                logger.error(f"WebSocket callback error: {e}")
    
    async def send_message(self, message: str):
        """
        Send message to WebSocket server
        
        Args:
            message: Message to send
        """
        if not self.is_connected:
            logger.error("Cannot send message: not connected")
            return
        
        try:
            await self.websocket.send(message)
            logger.debug(f"WebSocket message sent: {message}")
        except Exception as e:
            logger.error(f"WebSocket send error: {e}")


async def on_pcb_ready(message: str, timestamp: datetime):
    """
    Example callback function for PCB ready status
    
    Args:
        message: The ready message
        timestamp: When the message was received
    """
    print(f"[{timestamp}] PCB is ready: {message}")


