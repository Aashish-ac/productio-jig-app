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

def main():
    """Create or login admin account (smart unified flow)"""
    config = Config()
    db = Database(
        db_host=config.DB_HOST,
        db_port=config.DB_PORT,
        db_name=config.DB_NAME,
        db_user=config.DB_USER,
        db_password=config.DB_PASSWORD,
    )
    db.initialize()

    print("\n==== Admin CLI (Create or Login) ====")

    employee_id = input("Employee ID: ").strip()
    user = db.get_user_by_id(employee_id)
    if user and user.role == 'admin':
        # Admin account exists
        name_input = input("Name: ").strip()
        if user.name.strip().lower() != name_input.lower():
            print(f"Admin with ID {employee_id} already exists, but name does not match.\nPlease enter the correct name or choose a different ID.")
            db.close()
            return
        # Name matches, check password
        password = getpass("Password: ").strip()
        from database.models import bcrypt
        if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            print(f"Authenticated! Welcome back, {user.name} (ID: {employee_id})")
        else:
            print("Password incorrect. Access denied.")
        db.close()
        return
    else:
        # New admin registration
        name = input("Name: ").strip()
        password = getpass("Set Password: ").strip()
        if not employee_id or not name or not password:
            print("All fields (ID, name, password) are required. Aborting.")
            db.close()
            return
        admin_id = employee_id  # Use provided ID directly
        admin_user = db.create_user(
            employee_id=admin_id,
            name=name,
            password=password,
            role='admin',
            admin_id=None
        )
        if admin_user:
            print(f"Created admin: {admin_user.name} (ID: {admin_user.employee_id})")
        else:
            print("Failed to create admin (ID may already exist or DB error).")
        db.close()

if __name__ == "__main__":
    main()

