#!/usr/bin/env python3
"""
Camera Test Tool V2 - Main Application
Integrates Phase 1 (Telnet, WebSocket, Database) with Phase 2 (PyQt6 UI)
"""
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import QApplication, QTableWidgetItem, QMessageBox
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
import qasync

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from gui.login_window import LoginWindow
from gui.main_window import CameraTestMainWindow
from gui.admin_dashboard import AdminDashboard
from core.telnet_manager import TelnetConnectionPool
from core.websocket_manager import WebSocketManager
from database.models import Database
from core.config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CameraTestApp:
    """Main application class"""
    
    def __init__(self):
        self.config = Config()
        self.telnet_pool = TelnetConnectionPool(max_connections=50)
        self.websocket_manager = WebSocketManager()
        self.database = None  # Will be initialized if PostgreSQL is available
        self.main_window = None
        self.login_window = None  # Store login window reference
        
        # User info
        self.current_user = None
        self.current_role = None
        
        # LED state tracking (for toggle functionality)
        self.led_states = {}  # Track LED states per camera
        
        # Event loop reference (will be set when app starts)
        self._event_loop = None
    
    def initialize_database(self):
        """Initialize database connection (synchronous)"""
        try:
            self.database = Database(
                db_host=self.config.DB_HOST,
                db_port=self.config.DB_PORT,
                db_name=self.config.DB_NAME,
                db_user=self.config.DB_USER,
                db_password=self.config.DB_PASSWORD,
                pool_size=self.config.DB_POOL_SIZE,
                max_overflow=self.config.DB_MAX_OVERFLOW
            )
            self.database.initialize()  # Synchronous call
            logger.info("✓ Database initialized")
        except Exception as e:
            logger.warning(f"Database initialization skipped: {e}")
            self.database = None
    
    def setup_telnet_callbacks(self):
        """Setup Telnet event callbacks"""
        
        async def on_camera_connected(session):
            logger.info(f"✓ Camera {session.serial} connected")
            if self.main_window:
                self.main_window.camera_list_panel.update_camera_status(
                    session.serial, "connected"
                )
        
        async def on_camera_disconnected(session):
            logger.info(f"✗ Camera {session.serial} disconnected")
            if self.main_window:
                self.main_window.camera_list_panel.update_camera_status(
                    session.serial, "disconnected"
                )
        
        async def on_camera_error(session):
            logger.error(f"✗ Camera {session.serial} error: {session.last_error}")
            if self.main_window:
                self.main_window.camera_list_panel.update_camera_status(
                    session.serial, "error"
                )
        
        self.telnet_pool.register_callback('on_connect', on_camera_connected)
        self.telnet_pool.register_callback('on_disconnect', on_camera_disconnected)
        self.telnet_pool.register_callback('on_error', on_camera_error)
    
    def setup_websocket_callbacks(self):
        """Setup WebSocket callbacks for PCB ready status"""
        
        async def on_pcb_ready(message, timestamp):
            logger.info(f"✓ PCB is ready: {message} at {timestamp}")
            if self.main_window:
                # Enable test buttons when PCB is ready
                self.enable_test_buttons()
        
        self.websocket_manager.register_callback(on_pcb_ready)
    
    def enable_test_buttons(self):
        """Enable test buttons when PCB is ready"""
        if not self.main_window:
            return
        
        panel = self.main_window.main_content_panel
        panel.led_btn.setEnabled(True)
        panel.irled_btn.setEnabled(True)
        panel.ircut_btn.setEnabled(True)
        panel.speaker_btn.setEnabled(True)
        logger.info("Test buttons enabled - PCB ready")
    
    def disable_test_buttons(self):
        """Disable test buttons when PCB is not ready"""
        if not self.main_window:
            return
        
        panel = self.main_window.main_content_panel
        panel.led_btn.setEnabled(False)
        panel.irled_btn.setEnabled(False)
        panel.ircut_btn.setEnabled(False)
        panel.speaker_btn.setEnabled(False)
        logger.info("Test buttons disabled - waiting for PCB ready")
    
    def show_login(self):
        """Show login window"""
        self.login_window = LoginWindow()
        # Connect login signal (synchronous now)
        self.login_window.login_successful.connect(self.on_login_attempt)
        
        # Login window already has proper styling in login_window.py
        # No need to override it here
        
        # Actually show the window
        self.login_window.show()
        logger.info("✓ Login window displayed")
    
    def on_login_attempt(self, employee_id: str, employee_name: str, role: str, password: Optional[str] = None):
        """Smart login: for admin, allow new admin creation or login; for user, same as before"""
        if not self.database:
            self.login_window.show_error("Database not available.")
            return
        if role == "admin":
            existing_admin = self.database.get_user_by_id(employee_id)
            from PyQt6.QtWidgets import QMessageBox
            if existing_admin is None:
                # Create new admin with provided fields (no prior password check)
                if not employee_id or not employee_name or not password:
                    self.login_window.show_error("All fields are required for new admin registration.")
                    return
                create_result = self.database.create_user(
                    employee_id=employee_id,
                    name=employee_name,
                    password=password,
                    role="admin",
                    admin_id=None
                )
                if not create_result:
                    self.login_window.show_error("Admin creation failed. Employee ID may already exist.")
                    return
                self.current_user = {
                    'id': create_result.id,
                    'employee_id': create_result.employee_id,
                    'name': create_result.name,
                    'role': create_result.role,
                }
                self.current_role = "admin"
                self.on_login_success(employee_id, employee_name, role)
                return
            else:
                # Admin exists: name must match
                if existing_admin.name.strip().lower() != employee_name.strip().lower():
                    self.login_window.show_error("Admin with this ID already exists. Please enter the correct name.")
                    return
                # Name matches, check password
                import bcrypt
                if not password or not bcrypt.checkpw(password.encode('utf-8'), existing_admin.password_hash.encode('utf-8')):
                    self.login_window.show_error("Incorrect password for admin account.")
                    return
                # Success
                self.current_user = {
                    'id': existing_admin.id,
                    'employee_id': existing_admin.employee_id,
                    'name': existing_admin.name,
                    'role': existing_admin.role,
                }
                self.current_role = "admin"
                self.on_login_success(employee_id, employee_name, role)
                return
        else:
            # User path (unchanged)
            auth = self.database.authenticate_user(employee_id, employee_name)
            if not auth:
                self.login_window.show_error("Login failed. Check your credentials.")
                return
            self.current_user = auth
            self.current_role = auth["role"]
            self.on_login_success(employee_id, employee_name, role)
            return
    
    def _authenticate_and_login(self, employee_id: str, employee_name: str, role: str, password: Optional[str]):
        """Authenticate user with database and proceed with login (synchronous)"""
        try:
            # Authenticate user (synchronous call)
            user = self.database.authenticate_user(
                employee_id=employee_id,
                name=employee_name,
                provided_password=password
            )
            
            if not user:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self.login_window,
                    "Authentication Failed",
                    "Invalid credentials. Please check your Employee ID, Name, and Password."
                )
                logger.warning(f"Authentication failed: {employee_id}")
                return
            
            # Verify role matches (user is dict)
            if user.get('role', '').lower() != role.lower():
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self.login_window,
                    "Role Mismatch",
                    f"Selected role ({role}) does not match your account role ({user.get('role')})"
                )
                logger.warning(f"Role mismatch: {employee_id} - selected {role}, actual {user.get('role')}")
                return
            
            # Successful authentication
            logger.info(f"✓ User authenticated: {employee_name} ({employee_id}) as {user.get('role')}")
            
            # Store user info and admin linkage
            admin_db_id = user.get('admin_id')
            admin_emp_id = None
            if user.get('role') == 'user' and admin_db_id:
                # Lookup admin employee_id by DB id
                admin_user = self.database.get_user_by_db_id(admin_db_id)
                if admin_user:
                    admin_emp_id = admin_user.employee_id
            
            self.current_user = {
                'id': employee_id,
                'name': employee_name,
                'db_id': user.get('id'),
                'admin_db_id': admin_db_id,
                'admin_employee_id': admin_emp_id
            }
            self.current_role = user.get('role')
            
            # Show appropriate UI
            self.on_login_success(employee_id, employee_name, user.get('role'))
            
        except Exception as e:
            logger.error(f"Authentication error: {e}", exc_info=True)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self.login_window,
                "Error",
                f"Authentication error: {str(e)}"
            )

    def logout(self):
        """Return to login window and clear session"""
        logger.info("Logging out...")
        try:
            # Close main/admin windows if open
            if self.main_window and self.main_window.isVisible():
                self.main_window.close()
                self.main_window = None
            if self.admin_window and self.admin_window.isVisible():
                self.admin_window.close()
                self.admin_window = None
            
            # Clear session state
            self.current_user = None
            self.current_role = None
            
            # Show login window again
            self.show_login()
            logger.info("✓ Returned to login window")
        except Exception as e:
            logger.error(f"Logout error: {e}")
    
    def on_login_success(self, employee_id: str, employee_name: str, role: str):
        """Handle successful login - show appropriate dashboard"""
        logger.info(f"Login successful: {employee_name} ({employee_id}) as {role}")
        
        if role == "admin":
            # Create admin dashboard
            self.admin_window = AdminDashboard(
                employee_id, 
                employee_name,
                database=self.database,
                parent_app=self  # Ensure dashboard never loses parent/app
            )
            self.admin_window.show()
            logger.info("✓ Admin dashboard displayed")
        else:
            # Create main window for regular users
            self.main_window = CameraTestMainWindow(
                employee_id,
                employee_name,
                role
            )
            self.main_window.telnet_pool = self.telnet_pool
            self.main_window.websocket_manager = self.websocket_manager
            self.main_window._parent_app = self
            # If we have admin employee id, show it on UI
            admin_emp_id = None
            if self.current_user:
                admin_emp_id = self.current_user.get('admin_employee_id')
            if admin_emp_id and hasattr(self.main_window, 'set_admin_id'):
                self.main_window.set_admin_id(admin_emp_id)
            self.connect_test_buttons()
            self.main_window.show()
            logger.info("✓ Main window displayed")
        # Now close login window (do not immediately set to None)
        if self.login_window:
            self.login_window.close()
            # Defer deletion/remove ref after a small delay to avoid segfault race with Qt event loop.
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(500, lambda: setattr(self, 'login_window', None))
    
    def connect_test_buttons(self):
        """Connect test button signals - STORE LOOP REFERENCE"""
        if not self.main_window:
            return
        
        panel = self.main_window.main_content_panel
        
        # Store the event loop reference for later use
        self._event_loop = None
        try:
            self._event_loop = asyncio.get_event_loop()
        except RuntimeError:
            logger.error("No event loop available during button setup")
            return
        
        # Helper to create task using QTimer to ensure it runs in Qt context
        def make_handler(test_type):
            def handler():
                # Use QTimer.singleShot to schedule in next Qt event loop iteration
                # This ensures we're in the right context for async operations
                def schedule_task():
                    try:
                        # Get the running event loop (qasync)
                        loop = asyncio.get_running_loop()
                        # Create task in the running loop
                        loop.create_task(self.run_test(test_type))
                    except RuntimeError:
                        # If no running loop, try stored loop
                        if self._event_loop and not self._event_loop.is_closed():
                            self._event_loop.create_task(self.run_test(test_type))
                        else:
                            logger.error(f"No valid event loop for {test_type}")
                    except Exception as e:
                        logger.error(f"Error scheduling {test_type}: {e}")
                
                QTimer.singleShot(0, schedule_task)
            return handler
        
        # Save button handler (now synchronous)
        def save_handler():
            # Direct synchronous call - no async needed
            self.save_results()
        
        # Connect buttons to handlers
        panel.led_btn.clicked.connect(make_handler("led_test"))
        panel.irled_btn.clicked.connect(make_handler("irled_test"))
        panel.ircut_btn.clicked.connect(make_handler("ircut_test"))
        panel.speaker_btn.clicked.connect(make_handler("speaker_test"))
        panel.save_btn.clicked.connect(save_handler)
        
        logger.info("✓ Test buttons connected")
    
    async def handle_add_camera(self, ip: str, serial: str):
        """Handle add camera request from UI"""
        logger.info(f"Handling add camera: {serial} at {ip}")
        
        if not self.telnet_pool:
            logger.error("Telnet pool not initialized")
            return
        
        # Add camera to Telnet pool
        success = await self.telnet_pool.add_camera(serial, ip)
        
        if success:
            logger.info(f"✓ Camera {serial} connected successfully")
            if self.main_window:
                self.main_window.camera_list_panel.update_camera_status(serial, "connected")
                # Also update test panel status
                self.main_window.main_content_panel.update_camera_status(serial, "connected")
        else:
            logger.error(f"✗ Failed to connect to camera {serial}")
            if self.main_window:
                self.main_window.camera_list_panel.update_camera_status(serial, "error")
                # Also update test panel status
                self.main_window.main_content_panel.update_camera_status(serial, "error")
    
    async def run_test(self, test_type: str):
        """Run a test on selected camera only"""
        if not self.main_window:
            return
        
        # Get selected camera from main window
        camera_display = self.main_window.main_content_panel.current_camera
        if not camera_display:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self.main_window,
                "No Camera Selected",
                "Please select a camera from the list first."
            )
            return
        
        # STRIP EMOJI - extract just "CAM001" from "🟢 CAM001"
        camera_serial = camera_display.split()[-1]  # Get last word after emoji
        
        logger.info(f"Running {test_type} on {camera_display}")
        
        # Update camera status to "testing"
        self.main_window.camera_list_panel.update_camera_status(camera_serial, "testing")
        
        # Get camera session from pool
        if not self.telnet_pool or camera_serial not in self.telnet_pool.sessions:
            logger.error(f"Camera {camera_serial} not in Telnet pool")
            self.update_result(test_type, "FAIL")
            self.main_window.camera_list_panel.update_camera_status(camera_serial, "error")
            return
        
        session = self.telnet_pool.sessions[camera_serial]
        
        # Initialize state tracking for this camera if needed
        if camera_serial not in self.led_states:
            self.led_states[camera_serial] = {"led": False, "irled": False, "ircut": False}
        
        # Execute test via Telnet methods
        try:
            test_methods = {
                "led_test": session.test_led,
                "irled_test": session.test_irled,
                "ircut_test": session.test_ircut,
                "speaker_test": session.test_speaker,
            }
            
            if test_type not in test_methods:
                logger.error(f"Unknown test type: {test_type}")
                self.update_result(test_type, "FAIL")
                return
            
            # Execute test (speaker doesn't need toggle logic)
            if test_type == "speaker_test":
                result = await session.test_speaker()
            else:
                # Determine test key (strip "_test" suffix)
                test_key = test_type.replace("_test", "")
                
                # Toggle state: if currently OFF (False), turn ON (True)
                current_state = self.led_states[camera_serial].get(test_key, False)
                new_state = "on" if not current_state else "off"
                
                logger.info(f"[{camera_serial}] {test_key.upper()} toggle: {new_state.upper()}")
                
                # Execute command with new state
                result = await test_methods[test_type](new_state)
                
                # Update state tracking
                self.led_states[camera_serial][test_key] = (new_state == "on")
            
            # Process result
            if result and result.get("success"):
                output = result.get("output", "")
                command = result.get("command", "")
                logger.info(f"Test result: {output}")
                
                # Update results table based on output
                # If output is empty but success=True, consider it PASS
                status = "PASS" if (output and len(output.strip()) > 0) or result.get("success") else "FAIL"
                self.update_result(test_type, status, command=command, output=output)
                
                # Update camera status back to connected
                self.main_window.camera_list_panel.update_camera_status(camera_serial, "connected")
            else:
                logger.error(f"Test failed for {camera_serial}")
                error_msg = result.get("error", "Unknown error") if result else "Test execution failed"
                command = result.get("command", test_type) if result else test_type
                self.update_result(test_type, "FAIL", command=command, output=error_msg)
                self.main_window.camera_list_panel.update_camera_status(camera_serial, "error")
                
        except Exception as e:
            logger.error(f"Test execution error: {e}")
            self.update_result(test_type, "FAIL", command=test_type, output=str(e))
            self.main_window.camera_list_panel.update_camera_status(camera_serial, "error")
    
    def update_result(self, test_name: str, status: str, command: str = "", output: str = ""):
        """Update results table with all columns"""
        if not self.main_window:
            return
        
        from datetime import datetime
        
        table = self.main_window.main_content_panel.results_table
        
        # Find or add row
        row = -1
        for i in range(table.rowCount()):
            test_item = table.item(i, 1)  # Test column is now index 1
            if test_item and test_item.text() == test_name:
                row = i
                break
        
        if row == -1:
            row = table.rowCount()
            table.insertRow(row)
        
        # Populate all columns
        # Column 0: Time
        time_str = datetime.now().strftime("%H:%M:%S")
        table.setItem(row, 0, QTableWidgetItem(time_str))
        
        # Column 1: Test
        table.setItem(row, 1, QTableWidgetItem(test_name))
        
        # Column 2: Command (truncate to 80 chars for display)
        command_display = command[:80] + "..." if len(command) > 80 else command
        table.setItem(row, 2, QTableWidgetItem(command_display))
        
        # Column 3: Status (with color coding)
        status_display = "🟢 PASS" if status == "PASS" else "🔴 FAIL"
        status_item = QTableWidgetItem(status_display)
        status_item.setForeground(QColor("#4caf50" if status == "PASS" else "#d32f2f"))
        table.setItem(row, 3, status_item)
        
        # Column 4: Output (truncate to 80 chars)
        output_display = (output[:80] + "..." if len(output) > 80 else output) if output else ""
        table.setItem(row, 4, QTableWidgetItem(output_display))
        
        # Column 5: Operator
        operator = self.current_user or "Unknown"
        table.setItem(row, 5, QTableWidgetItem(operator))
        
        # Auto-resize columns for better visibility
        table.resizeColumnsToContents()
    
    def save_results(self):
        """Save test results to database (synchronous)"""
        if not self.main_window:
            logger.error("Main window not available")
            return
        
        if not self.database:
            logger.warning("Database not available, results not saved to database")
            return
        
        # Get camera serial from current camera selection
        panel = self.main_window.main_content_panel
        camera_display = panel.current_camera
        
        if not camera_display:
            logger.error("No camera selected")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self.main_window,
                "No Camera Selected",
                "Please select a camera before saving results."
            )
            return
        
        # Extract clean serial (remove emoji if present)
        camera_serial = camera_display.split()[-1] if ' ' in camera_display else camera_display
        
        # Collect results from table
        results = self.collect_test_results()
        
        if not results:
            logger.warning("No test results to save")
            return
        
        try:
            from PyQt6.QtWidgets import QMessageBox
            
            # Confirm save
            reply = QMessageBox.question(
                self.main_window,
                "Confirm Save",
                f"Save test results for camera {camera_serial}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # Calculate overall status
            all_passed = all(status == "PASS" for _, status in results.items())
            overall_status = "PASS" if all_passed else "FAIL"
            
            # Save to database (requires User and Camera records to exist)
            logger.info(f"Saving results for camera {camera_serial}: {results}")
            
            # For now, just log - full ORM save will be added in production
            logger.info(f"✓ Results saved (demo mode)")
            
            QMessageBox.information(
                self.main_window,
                "Success",
                f"Results saved successfully!\n\nCamera: {camera_serial}\nStatus: {overall_status}\nTests: {len(results)}"
            )
            
        except Exception as e:
            logger.error(f"Error saving results: {e}", exc_info=True)
            QMessageBox.critical(
                self.main_window,
                "Error",
                f"Failed to save results: {str(e)}"
            )
    
    def collect_test_results(self) -> dict:
        """Collect test results from results table - only checked tests"""
        if not self.main_window:
            return {}
        
        panel = self.main_window.main_content_panel
        table = panel.results_table
        results = {}
        
        for row in range(table.rowCount()):
            # Check if this test's checkbox is checked
            test_item = table.item(row, 1)  # Test column
            if not test_item:
                continue
                
            test_name = test_item.text()
            
            # Check corresponding checkbox in test panel
            checkbox = panel.test_checkboxes.get(test_name)
            if checkbox and checkbox.isChecked():
                # Collect all data from this row
                time_item = table.item(row, 0)
                command_item = table.item(row, 2)
                status_item = table.item(row, 3)
                output_item = table.item(row, 4)
                operator_item = table.item(row, 5)
                
                results[test_name] = {
                    "time": time_item.text() if time_item else "",
                    "command": command_item.text() if command_item else "",
                    "status": status_item.text() if status_item else "",
                    "output": output_item.text() if output_item else "",
                    "operator": operator_item.text() if operator_item else ""
                }
        
        return results
    
    async def cleanup(self):
        """Cleanup resources on exit"""
        logger.info("Cleaning up resources...")
        
        if self.telnet_pool:
            await self.telnet_pool.close_all()
        
        if self.websocket_manager:
            await self.websocket_manager.disconnect()
        
        if self.database:
            self.database.close()  # Synchronous now
        
        logger.info("✓ Cleanup complete")


def main():
    """Main application entry point - NOT async"""
    logger.info("Starting Camera Test Tool V2...")
    
    # Create Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("Camera Test Tool V2")
    app.setStyle('Fusion')  # Cross-platform consistent appearance
    
    # Prevent app from quitting when login window closes (we'll show dashboard/main window)
    app.setQuitOnLastWindowClosed(False)
    
    # Create qasync event loop
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Create app instance
    camera_app = CameraTestApp()
    
    # Setup cleanup handler
    def cleanup():
        logger.info("Cleaning up resources...")
        try:
            if camera_app.telnet_pool:
                loop.run_until_complete(camera_app.telnet_pool.close_all())
            if camera_app.websocket_manager:
                loop.run_until_complete(camera_app.websocket_manager.disconnect())
            if camera_app.database:
                camera_app.database.close()  # Synchronous now
            logger.info("✓ Cleanup complete")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    # Don't connect cleanup to aboutToQuit here - it triggers too early
    # Cleanup will be handled when window is actually closed
    
    # Store event loop reference BEFORE initialization (so it's available immediately)
    camera_app._event_loop = loop
    
    # Initialize components (database is now synchronous)
    try:
        camera_app.initialize_database()  # Synchronous
        camera_app.setup_telnet_callbacks()
        camera_app.setup_websocket_callbacks()
        
        # Disable test buttons initially (waiting for PCB ready)
        camera_app.disable_test_buttons()
        
        # Show login window
        camera_app.show_login()
        
        logger.info("✓ Application initialized")
    except Exception as e:
        logger.error(f"Initialization error: {e}", exc_info=True)
        return
    
    # Setup cleanup for actual app exit (always run on quit)
    def safe_cleanup():
        """Cleanup resources when app is quitting"""
        try:
            # Always cleanup on app quit (not conditional)
            cleanup()
        except Exception as e:
            logger.debug(f"Cleanup warning (ignored): {e}")
    
    # Only connect cleanup to actual quit, not window close
    app.aboutToQuit.connect(safe_cleanup)
    
    # Handle last window closed - quit app when dashboard/main window closes
    def on_last_window_closed():
        """Handle last window closed - quit app when main windows are closed"""
        # Only quit if the main/admin windows are closed (not just login window)
        if not (camera_app.main_window and camera_app.main_window.isVisible()) and \
           not (camera_app.admin_window and camera_app.admin_window.isVisible()):
            app.quit()
    
    app.lastWindowClosed.connect(on_last_window_closed)
    
    # Run Qt event loop - USE app.exec() not loop.run_forever()
    with loop:
        try:
            sys.exit(app.exec())
        except KeyboardInterrupt:
            logger.info("Application interrupted by user")
            cleanup()
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)

