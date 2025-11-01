"""
Network utilities for IP validation and ping
"""
import asyncio
import logging
import subprocess
import platform

logger = logging.getLogger(__name__)


def ping_ip_sync(ip: str, timeout: int = 3) -> bool:
    """
    Ping IP address synchronously (for use when no event loop is available)
    
    Args:
        ip: IP address to ping
        timeout: Timeout in seconds
        
    Returns:
        True if ping successful, False otherwise
    """
    try:
        # Determine ping command based on OS
        if platform.system().lower() == "windows":
            cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), ip]
        else:
            # Linux/Mac
            cmd = ["ping", "-c", "1", "-W", str(timeout), ip]
        
        # Execute ping synchronously
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout + 1  # Add buffer
        )
        
        if result.returncode == 0:
            logger.info(f"✓ Ping successful: {ip}")
            return True
        else:
            # Log the actual error message from ping
            error_msg = result.stderr.decode('utf-8', errors='ignore').strip() if result.stderr else ""
            stdout_msg = result.stdout.decode('utf-8', errors='ignore').strip() if result.stdout else ""
            
            if error_msg:
                logger.warning(f"✗ Ping failed: {ip} (return code: {result.returncode}) - {error_msg}")
            elif stdout_msg:
                logger.warning(f"✗ Ping failed: {ip} (return code: {result.returncode}) - {stdout_msg}")
            else:
                # Common return codes and their meanings
                error_meaning = {
                    1: "no response received",
                    2: "no route to host or network unreachable"
                }.get(result.returncode, "unknown error")
                logger.warning(f"✗ Ping failed: {ip} (return code: {result.returncode}, {error_meaning})")
            return False
            
    except FileNotFoundError:
        logger.warning(f"Ping command not available, skipping validation for {ip}")
        return True  # Assume success if ping not available
    except subprocess.TimeoutExpired:
        logger.warning(f"✗ Ping timeout: {ip}")
        return False
    except Exception as e:
        logger.error(f"Ping error for {ip}: {e}")
        return False


async def ping_ip(ip: str, timeout: int = 3) -> bool:
    """
    Ping IP address to verify network connectivity
    
    Uses run_in_executor to run the sync ping in a thread pool, which is safer
    with qasync event loop and avoids subprocess event loop issues.
    
    Args:
        ip: IP address to ping
        timeout: Timeout in seconds
        
    Returns:
        True if ping successful, False otherwise
    """
    # Check if we have a running event loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, use sync version directly
        logger.debug("No running event loop, using sync ping")
        return ping_ip_sync(ip, timeout)
    
    try:
        # Use run_in_executor with None (default thread pool) to run sync ping
        # This preserves the event loop context better than to_thread for qasync
        result = await loop.run_in_executor(None, ping_ip_sync, ip, timeout)
        return result
    except Exception as e:
        logger.error(f"Ping error for {ip}: {e}")
        # Fall back to sync if executor fails
        return ping_ip_sync(ip, timeout)


async def validate_camera_ip(ip: str, port: int = 23) -> tuple[bool, str]:
    """
    Validate camera IP and port availability
    
    Args:
        ip: IP address to validate
        port: Port number to check
        
    Returns:
        (success, message) tuple
    """
    # First, ping the IP
    ping_result = await ping_ip(ip)
    
    if not ping_result:
        return False, f"Camera not responding at {ip} (ping failed)"
    
    # Then check if port is open (optional)
    # For now, skip port check and just report ping result
    logger.info(f"✓ Camera IP validated: {ip}:{port}")
    return True, f"Camera responding at {ip}"

