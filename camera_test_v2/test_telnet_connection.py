#!/usr/bin/env python3
"""
Test Telnet Connection to Camera
Verifies camera is reachable and can execute commands via Telnet
"""
import asyncio
import logging
from pathlib import Path
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from core.telnet_manager import TelnetConnectionPool, CameraSession
from core.network_utils import ping_ip, validate_camera_ip

async def test_single_camera(ip: str, username: str = "root", password: str = ""):
    """Test connection to a single camera"""
    print("=" * 70)
    print(f"Testing Telnet Connection to Camera: {ip}")
    print("=" * 70)
    
    # Step 1: Ping Test
    print("\n[1/4] Ping Test...")
    ping_result = await ping_ip(ip, timeout=3)
    if ping_result:
        print("   ✓ Camera is reachable via ping")
    else:
        print("   ✗ Camera NOT reachable - check IP address and network")
        return False
    
    # Step 2: Telnet Port Check (optional - can skip)
    print("\n[2/4] Telnet Port Check...")
    print(f"   Attempting to connect to {ip}:23")
    
    # Step 3: Create Telnet Session
    print("\n[3/4] Creating Telnet Session...")
    session = CameraSession(
        serial=f"TEST_{ip.split('.')[-1]}",
        ip=ip
    )
    
    try:
        # Connect with authentication
        print(f"   Connecting as {username}...")
        connected = await session.connect(
            username=username,
            password=password,
            timeout=10
        )
        
        if connected:
            print("   ✓ Telnet connection established!")
        else:
            print("   ✗ Telnet connection failed")
            print(f"   Error: {session.last_error}")
            return False
        
        # Step 4: Execute Test Command
        print("\n[4/4] Testing Command Execution...")
        test_command = "ps"
        print(f"   Executing: {test_command}")
        
        result = await session.execute_command(test_command, timeout=5)
        
        if result:
            print(f"   ✓ Command executed successfully!")
            print(f"   Response: {result[:100]}...")
            return True
        else:
            print(f"   ✗ Command execution failed")
            print(f"   Error: {session.last_error}")
            return False
            
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    finally:
        # Cleanup
        await session.disconnect()
        print("\n✓ Disconnected from camera")
        print("=" * 70)


async def test_with_pool(ip: str):
    """Test using TelnetConnectionPool"""
    print("\n\nTesting with Connection Pool:")
    print("=" * 70)
    
    pool = TelnetConnectionPool(max_connections=10)
    
    camera_id = f"TEST_{ip.replace('.', '_')}"
    
    print(f"\nAdding camera {camera_id} ({ip}) to pool...")
    success = await pool.add_camera(camera_id, ip)
    
    if success:
        print(f"✓ Camera added successfully!")
        
        # Check status
        status = await pool.get_session_status(camera_id)
        if status:
            print(f"   Serial: {status['serial']}")
            print(f"   IP: {status['ip']}")
            print(f"   State: {status['state']}")
            print(f"   Connected: {status['connected']}")
        
        # Execute a test
        print(f"\nTesting LED command...")
        result = await pool.execute_command(camera_id, "ps")
        if result:
            print(f"✓ Command successful: {result[:50]}...")
        
        # Cleanup
        await pool.remove_camera(camera_id)
    else:
        print(f"✗ Failed to add camera")
    
    await pool.close_all()


async def main():
    """Main test function"""
    print("\n" + "=" * 70)
    print("Camera Telnet Connection Test Tool")
    print("=" * 70)
    
    # Get IP from user
    if len(sys.argv) > 1:
        camera_ip = sys.argv[1]
    else:
        camera_ip = input("\nEnter camera IP address: ").strip()
    
    if not camera_ip:
        print("No IP provided. Exiting.")
        return
    
    # Test single camera
    await test_single_camera(camera_ip)
    
    # Test with pool
    await test_with_pool(camera_ip)
    
    print("\n✓ Testing complete!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

