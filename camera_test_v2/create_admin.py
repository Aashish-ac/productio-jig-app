#!/usr/bin/env python3
"""
Script to create initial admin account
Run this once to set up the first admin user
"""
import sys
from pathlib import Path
from getpass import getpass

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from database.models import Database
from core.config import Config

def create_admin():
    """Create initial admin account (synchronous)"""
    config = Config()
    
    # Initialize database
    db = Database(
        db_host=config.DB_HOST,
        db_port=config.DB_PORT,
        db_name=config.DB_NAME,
        db_user=config.DB_USER,
        db_password=config.DB_PASSWORD
    )
    
    # Initialize tables (synchronous)
    db.initialize()
    
    # Get admin details
    print("=" * 60)
    print("Create Initial Admin Account")
    print("=" * 60)
    
    name = input("Enter Admin Full Name: ").strip()
    password = getpass("Enter Admin Password: ").strip()
    
    if not name or not password:
        print("Error: Name and password are required")
        db.close()
        return
    
    # Generate admin ID (synchronous)
    admin_id = db.generate_next_employee_id("ADM")
    
    # Create admin user (synchronous)
    admin_user = db.create_user(
        employee_id=admin_id,
        name=name,
        password=password,
        role="admin",
        admin_id=None  # Admins don't have an admin_id
    )
    
    if admin_user:
        print("\n" + "=" * 60)
        print("✓ Admin Account Created Successfully!")
        print("=" * 60)
        print(f"Employee ID: {admin_id}")
        print(f"Name: {name}")
        print(f"Password: {password}")
        print("\nUse these credentials to login as Admin.")
        print("=" * 60)
    else:
        print("\n✗ Failed to create admin account")
        print("(User might already exist)")
    
    db.close()

if __name__ == "__main__":
    create_admin()

