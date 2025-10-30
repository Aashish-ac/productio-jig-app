"""
Professional Admin Dashboard for User Management and Result Tracking
Matches main window styling and includes full functionality
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QLineEdit, QComboBox, QHeaderView,
    QMessageBox, QListWidget, QListWidgetItem, QSplitter, QGroupBox, QFormLayout, QScrollArea,
    QDateEdit, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QTimer
from PyQt6.QtGui import QColor, QFont
import logging
import asyncio
import qasync
from datetime import datetime, timedelta
from pathlib import Path
import csv

logger = logging.getLogger(__name__)


class HeaderBar(QWidget):
    """Top header bar matching main window - FIXED"""
    def __init__(self, user_name: str, employee_id: str):
        super().__init__()
        self.user_name = user_name
        self.employee_id = employee_id
        self.on_logout_requested = None  # callback set by dashboard
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 8, 20, 8)
        
        # User info on left
        user_info = QLabel(f"👤 Admin: {self.user_name} ({self.employee_id})")
        user_info.setStyleSheet("font-size: 13px; color: #fff;")
        layout.addWidget(user_info)
        
        # Spacer
        layout.addStretch()
        
        # Logout button
        logout_btn = QPushButton("Logout")
        logout_btn.setFixedHeight(28)
        logout_btn.setStyleSheet("QPushButton { background-color: #d9534f; color: #fff; border: none; padding: 6px 12px; border-radius: 4px; } QPushButton:hover { background-color: #c9302c; }")
        logout_btn.clicked.connect(self._handle_logout)
        layout.addWidget(logout_btn)
        
        # Company name on right
        company_name = QLabel("Actoan")
        company_name.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4;")
        company_name.setWordWrap(False)
        company_name.setMinimumWidth(100)
        layout.addWidget(company_name, alignment=Qt.AlignmentFlag.AlignRight)
        
        self.setLayout(layout)
        self.setStyleSheet("background-color: #1e1e1e; border-bottom: 1px solid #3d3d3d;")
        self.setFixedHeight(40)
    
    def _handle_logout(self):
        if callable(self.on_logout_requested):
            self.on_logout_requested()


class UserListWidget(QWidget):
    """Left panel: User list - Matching main window style"""
    user_selected = pyqtSignal(dict)  # Emits user data
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Title
        title = QLabel("👥 Users")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #fff; margin-bottom: 5px;")
        layout.addWidget(title)
        
        # User list
        self.user_list = QListWidget()
        self.user_list.setStyleSheet(self.get_list_style())
        self.user_list.itemClicked.connect(self.on_user_clicked)
        layout.addWidget(self.user_list)
        
        # Add button
        add_btn = QPushButton("➕ Add User")
        add_btn.setStyleSheet(self.get_button_style("#4caf50"))
        add_btn.setFixedHeight(38)
        add_btn.clicked.connect(self.emit_add_request)
        layout.addWidget(add_btn)
        
        self.setLayout(layout)
    
    def emit_add_request(self):
        """Emit signal for add user"""
        self.user_selected.emit({'action': 'add'})
    
    def on_user_clicked(self, item):
        """Handle user selection"""
        user_data = item.data(Qt.ItemDataRole.UserRole)
        if user_data:
            self.user_selected.emit(user_data)
    
    def add_user(self, user_data: dict):
        """Add user to list with admin_id display"""
        name = user_data.get('name', 'Unknown')
        emp_id = user_data.get('employee_id', 'N/A')
        admin_id = user_data.get('admin_id')
        
        # Display with admin_id if available
        if admin_id:
            item_text = f"👤 {name} ({emp_id}) [Admin ID: {admin_id}]"
        else:
            item_text = f"👤 {name} ({emp_id})"
        
        item = QListWidgetItem(item_text)
        item.setData(Qt.ItemDataRole.UserRole, user_data)
        self.user_list.addItem(item)
    
    def clear_users(self):
        """Clear all users from list"""
        self.user_list.clear()
    
    def get_list_style(self):
        return """
            QListWidget {
                background-color: #252526;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                color: #fff;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #3d3d3d;
                font-size: 12px;
            }
            QListWidget::item:hover {
                background-color: #2d2d2d;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
        """
    
    def get_button_style(self, color: str):
        return f"""
            QPushButton {{
                background-color: {color};
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: bold;
                color: white;
            }}
            QPushButton:hover {{
                opacity: 0.85;
            }}
        """


class UserManagementPanel(QWidget):
    """User creation/editing panel - Professional styling"""
    save_user_requested = pyqtSignal(dict)  # Emits user data to save
    delete_user_requested = pyqtSignal(str)  # Emits employee_id to delete
    
    def __init__(self):
        super().__init__()
        self.current_user_id = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(12)
        
        frame = QFrame()
        frame.setStyleSheet("background-color: #252526; border-radius: 6px; padding: 10px;")
        frame_layout = QVBoxLayout()
        frame_layout.setSpacing(8)
        
        # Title
        title = QLabel("👤 User Management")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0078d4;")
        frame_layout.addWidget(title)
        
        # Form
        form_group = QGroupBox()
        form_group.setStyleSheet("border: none; color: #fff;")
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Employee ID (auto-generated, readonly for new users)
        self.employee_id_input = QLineEdit()
        self.employee_id_input.setPlaceholderText("Auto-generated (e.g., USR001)")
        self.employee_id_input.setReadOnly(True)
        self.employee_id_input.setStyleSheet("padding: 8px; border-radius: 4px; background-color: #2d2d2d; color: #888;")
        self.employee_id_input.setFixedHeight(32)
        form_layout.addRow("Employee ID:", self.employee_id_input)
        
        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter full name")
        self.name_input.setStyleSheet("padding: 8px; border-radius: 4px; background-color: #1e1e1e; color: #fff;")
        self.name_input.setFixedHeight(32)
        self.name_input.textChanged.connect(self.update_password_preview)
        form_layout.addRow("Full Name:", self.name_input)
        
        # Password (auto-generated, readonly)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Auto: Employee ID + Name")
        self.password_input.setReadOnly(True)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
        self.password_input.setStyleSheet("padding: 8px; border-radius: 4px; background-color: #2d2d2d; color: #888;")
        self.password_input.setFixedHeight(32)
        form_layout.addRow("Password:", self.password_input)
        
        # Info label
        info_label = QLabel("ℹ️ Password will be: Employee ID + Name")
        info_label.setStyleSheet("color: #666; font-size: 11px; margin-top: -5px; margin-bottom: 10px;")
        form_layout.addRow("", info_label)
        
        # Role (readonly for admin-created users)
        self.role_label = QLabel("user")
        self.role_label.setStyleSheet("color: #888; font-size: 12px;")
        form_layout.addRow("Role:", self.role_label)
        
        form_group.setLayout(form_layout)
        frame_layout.addWidget(form_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.save_btn = QPushButton("💾 Save User")
        self.save_btn.setStyleSheet(self.get_button_style("#0078d4"))
        self.save_btn.setFixedHeight(32)
        self.save_btn.clicked.connect(self.on_save)
        btn_layout.addWidget(self.save_btn)
        
        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.setStyleSheet(self.get_button_style("#d32f2f"))
        self.delete_btn.setFixedHeight(32)
        self.delete_btn.clicked.connect(self.on_delete)
        btn_layout.addWidget(self.delete_btn)
        
        self.clear_btn = QPushButton("🔄 Clear")
        self.clear_btn.setStyleSheet(self.get_button_style("#666"))
        self.clear_btn.setFixedHeight(32)
        self.clear_btn.clicked.connect(self.clear_form)
        btn_layout.addWidget(self.clear_btn)
        
        frame_layout.addLayout(btn_layout)
        frame.setLayout(frame_layout)
        layout.addWidget(frame)
        
        self.setLayout(layout)
    
    def load_user(self, user_data: dict):
        """Load user data into form"""
        self.current_user_id = user_data.get('employee_id')
        self.employee_id_input.setText(user_data.get('employee_id', ''))
        self.name_input.setText(user_data.get('name', ''))
        self.employee_id_input.setEnabled(False)  # Cannot change employee_id
        self.delete_btn.setEnabled(True)
    
    def clear_form(self):
        """Clear form for new user"""
        self.current_user_id = None
        self.employee_id_input.clear()
        self.employee_id_input.setReadOnly(True)
        self.employee_id_input.setPlaceholderText("Auto-generated (e.g., USR001)")
        self.name_input.clear()
        self.password_input.clear()
        self.password_input.setPlaceholderText("Auto: Employee ID + Name")
        self.delete_btn.setEnabled(False)
    
    def update_password_preview(self):
        """Update password preview when name changes"""
        emp_id = self.employee_id_input.text().strip()
        name = self.name_input.text().strip()
        if emp_id and name:
            self.password_input.setText(f"{emp_id}{name}")
        else:
            self.password_input.clear()
    
    def on_save(self):
        """Handle save button click"""
        employee_id = self.employee_id_input.text().strip()
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter Full Name")
            return
        
        # For new users: employee_id will be auto-generated
        # For existing users: employee_id is already set
        if not employee_id and not self.current_user_id:
            # This will trigger auto-generation in backend
            employee_id = None
        
        # Password is always auto-generated: employee_id + name
        password = f"{employee_id}{name}" if employee_id else None
        
        user_data = {
            'employee_id': employee_id,  # None for new users (will be auto-generated)
            'name': name,
            'password': password,  # Will be employee_id + name
            'role': 'user'
        }
        
        self.save_user_requested.emit(user_data)
    
    def on_delete(self):
        """Handle delete button click"""
        if not self.current_user_id:
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete user {self.current_user_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.delete_user_requested.emit(self.current_user_id)
    
    def get_button_style(self, color: str):
        return f"""
            QPushButton {{
                background-color: {color};
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: bold;
                color: white;
            }}
            QPushButton:hover {{
                opacity: 0.85;
            }}
            QPushButton:disabled {{
                background-color: #555;
                color: #888;
            }}
        """


class ResultsPanel(QWidget):
    """Test results panel with filtering and export - Professional styling"""
    export_requested = pyqtSignal(str)  # Emits export format ('csv' or 'pdf')
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(12)
        
        frame = QFrame()
        frame.setStyleSheet("background-color: #252526; border-radius: 6px; padding: 10px;")
        frame_layout = QVBoxLayout()
        frame_layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("📊 Test Results")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0078d4;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Export button
        export_btn = QPushButton("📥 Export CSV")
        export_btn.setStyleSheet(self.get_button_style("#4caf50"))
        export_btn.setFixedHeight(32)
        export_btn.clicked.connect(lambda: self.export_requested.emit('csv'))
        header_layout.addWidget(export_btn)
        
        frame_layout.addLayout(header_layout)
        
        # Filters
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)
        
        # User filter
        filter_layout.addWidget(QLabel("User:"))
        self.user_filter = QComboBox()
        self.user_filter.setEditable(True)
        self.user_filter.setPlaceholderText("All Users")
        self.user_filter.setStyleSheet("padding: 8px; border-radius: 4px; background-color: #1e1e1e; color: #fff; min-width: 150px;")
        self.user_filter.setFixedHeight(32)
        filter_layout.addWidget(self.user_filter)
        
        # Status filter
        filter_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "PASS", "FAIL"])
        self.status_filter.setStyleSheet("padding: 8px; border-radius: 4px; background-color: #1e1e1e; color: #fff;")
        self.status_filter.setFixedHeight(32)
        filter_layout.addWidget(self.status_filter)
        
        # Date filter
        filter_layout.addWidget(QLabel("Date:"))
        self.date_filter = QComboBox()
        self.date_filter.addItems(["All", "Today", "Last 7 Days", "Last 30 Days", "Custom"])
        self.date_filter.setStyleSheet("padding: 8px; border-radius: 4px; background-color: #1e1e1e; color: #fff;")
        self.date_filter.setFixedHeight(32)
        filter_layout.addWidget(self.date_filter)
        
        # Apply filter button
        apply_btn = QPushButton("🔍 Apply Filters")
        apply_btn.setStyleSheet(self.get_button_style("#0078d4"))
        apply_btn.setFixedHeight(32)
        apply_btn.clicked.connect(self.emit_apply_filters)
        filter_layout.addWidget(apply_btn)
        
        frame_layout.addLayout(filter_layout)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels([
            "User", "Employee ID", "Camera Serial", "LED", "IRLED", "IRCUT", "Speaker", "Date"
        ])
        self.results_table.setStyleSheet(self.get_table_style())
        self.results_table.setMinimumHeight(400)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        frame_layout.addWidget(self.results_table)
        
        frame.setLayout(frame_layout)
        layout.addWidget(frame)
        self.setLayout(layout)
    
    def emit_apply_filters(self):
        """Emit signal to apply filters - handled by parent"""
        if hasattr(self, 'parent_dashboard'):
            self.parent_dashboard.apply_results_filters()
    
    def populate_table(self, results: list):
        """Populate results table"""
        self.results_table.setRowCount(0)
        
        for result in results:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            
            # User
            self.results_table.setItem(row, 0, QTableWidgetItem(result.get('user_name', 'Unknown')))
            # Employee ID
            self.results_table.setItem(row, 1, QTableWidgetItem(result.get('employee_id', 'N/A')))
            # Camera Serial
            self.results_table.setItem(row, 2, QTableWidgetItem(result.get('camera_serial', 'N/A')))
            # LED
            led_status = result.get('led_test', 'N/A')
            item = QTableWidgetItem(led_status)
            item.setForeground(QColor("#4caf50" if led_status == "PASS" else "#d32f2f"))
            self.results_table.setItem(row, 3, item)
            # IRLED
            irled_status = result.get('irled_test', 'N/A')
            item = QTableWidgetItem(irled_status)
            item.setForeground(QColor("#4caf50" if irled_status == "PASS" else "#d32f2f"))
            self.results_table.setItem(row, 4, item)
            # IRCUT
            ircut_status = result.get('ircut_test', 'N/A')
            item = QTableWidgetItem(ircut_status)
            item.setForeground(QColor("#4caf50" if ircut_status == "PASS" else "#d32f2f"))
            self.results_table.setItem(row, 5, item)
            # Speaker
            speaker_status = result.get('speaker_test', 'N/A')
            item = QTableWidgetItem(speaker_status)
            item.setForeground(QColor("#4caf50" if speaker_status == "PASS" else "#d32f2f"))
            self.results_table.setItem(row, 6, item)
            # Date
            test_date = result.get('test_date', '')
            if isinstance(test_date, datetime):
                date_str = test_date.strftime("%Y-%m-%d %H:%M")
            else:
                date_str = str(test_date)
            self.results_table.setItem(row, 7, QTableWidgetItem(date_str))
        
        self.results_table.resizeColumnsToContents()
    
    def get_all_results(self) -> list:
        """Get all results from table"""
        results = []
        for row in range(self.results_table.rowCount()):
            results.append({
                'user': self.results_table.item(row, 0).text() if self.results_table.item(row, 0) else '',
                'employee_id': self.results_table.item(row, 1).text() if self.results_table.item(row, 1) else '',
                'camera_serial': self.results_table.item(row, 2).text() if self.results_table.item(row, 2) else '',
                'led': self.results_table.item(row, 3).text() if self.results_table.item(row, 3) else '',
                'irled': self.results_table.item(row, 4).text() if self.results_table.item(row, 4) else '',
                'ircut': self.results_table.item(row, 5).text() if self.results_table.item(row, 5) else '',
                'speaker': self.results_table.item(row, 6).text() if self.results_table.item(row, 6) else '',
                'date': self.results_table.item(row, 7).text() if self.results_table.item(row, 7) else '',
            })
        return results
    
    def get_filter_params(self) -> dict:
        """Get current filter parameters"""
        user_filter = self.user_filter.currentText()
        status_filter = self.status_filter.currentText()
        date_filter = self.date_filter.currentText()
        
        params = {}
        if user_filter and user_filter != "All Users":
            params['user'] = user_filter
        if status_filter != "All":
            params['status'] = status_filter
        
        # Date range
        if date_filter == "Today":
            params['start_date'] = datetime.now().replace(hour=0, minute=0, second=0)
            params['end_date'] = datetime.now()
        elif date_filter == "Last 7 Days":
            params['start_date'] = datetime.now() - timedelta(days=7)
            params['end_date'] = datetime.now()
        elif date_filter == "Last 30 Days":
            params['start_date'] = datetime.now() - timedelta(days=30)
            params['end_date'] = datetime.now()
        
        return params
    
    def populate_user_filter(self, users: list):
        """Populate user filter dropdown"""
        self.user_filter.clear()
        self.user_filter.addItem("All Users")
        for user in users:
            display_name = f"{user.get('name', 'Unknown')} ({user.get('employee_id', 'N/A')})"
            self.user_filter.addItem(display_name, user.get('employee_id'))
    
    def get_button_style(self, color: str):
        return f"""
            QPushButton {{
                background-color: {color};
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: bold;
                color: white;
            }}
            QPushButton:hover {{
                opacity: 0.85;
            }}
        """
    
    def get_table_style(self):
        return """
            QTableWidget {
                background-color: #1e1e1e;
                border: 2px solid #3d3d3d;
                border-radius: 5px;
                gridline-color: #3d3d3d;
                color: #e6e6e6;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QTableWidget::item:alternate {
                background-color: #252526;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #fff;
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }
        """


class AdminDashboard(QMainWindow):
    """Complete Admin Dashboard - Professional UI matching main window"""
    
    def __init__(self, admin_id: str, admin_name: str, database=None, parent_app=None):
        super().__init__()
        self.admin_id = admin_id
        self.admin_name = admin_name
        self.database = database
        self.parent_app = parent_app
        self.setWindowTitle("Camera Test Tool - Admin Dashboard")
        self.setMinimumSize(1500, 900)
        self.setStyleSheet("background-color: #1e1e1e; color: #fff;")
        self.init_ui()
        
        # Load data asynchronously
        if self.database:
            QTimer.singleShot(100, self.load_initial_data)
    
    def init_ui(self):
        # Header
        self.header_bar = HeaderBar(self.admin_name, self.admin_id)
        # Wire logout
        def do_logout():
            if self.parent_app:
                self.parent_app.logout()
        self.header_bar.on_logout_requested = do_logout
        
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.header_bar)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: User list
        self.user_list_panel = UserListWidget()
        self.user_list_panel.setMinimumWidth(250)
        self.user_list_panel.setMaximumWidth(280)
        self.user_list_panel.user_selected.connect(self.on_user_action)
        splitter.addWidget(self.user_list_panel)
        
        # Right panel: Content
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # User management panel
        self.user_mgmt_panel = UserManagementPanel()
        self.user_mgmt_panel.save_user_requested.connect(self.on_save_user)
        self.user_mgmt_panel.delete_user_requested.connect(self.on_delete_user)
        content_layout.addWidget(self.user_mgmt_panel)
        
        # Results panel
        self.results_panel = ResultsPanel()
        self.results_panel.parent_dashboard = self  # Reference for filter apply
        self.results_panel.export_requested.connect(self.on_export)
        content_layout.addWidget(self.results_panel)
        
        content_widget.setLayout(content_layout)
        splitter.addWidget(content_widget)
        
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
    
    def load_initial_data(self):
        """Load initial data from database"""
        if not self.database:
            return
        
        # Load data synchronously (database is now sync)
        QTimer.singleShot(100, self.load_initial_data_sync)
    
    def load_initial_data_sync(self):
        """Load initial data synchronously"""
        self.load_users()
        self.load_results()
    
    def load_users(self):
        """Load users from database (synchronous)"""
        if not self.database:
            return
        
        try:
            # Get admin user to get admin_id for filtering
            admin_user = self.database.get_user_by_id(self.admin_id)
            admin_db_id = admin_user.id if admin_user else None
            
            users = self.database.get_all_users(admin_id=admin_db_id)
            
            # Update UI in main thread (using QTimer for thread safety)
            user_list_data = []
            for user in users:
                if user.is_active:
                    user_data = {
                        'employee_id': user.employee_id,
                        'name': user.name,
                        'role': user.role,
                        'id': user.id,
                        'admin_id': user.admin_id  # Include admin_id
                    }
                    user_list_data.append({
                        'name': user.name,
                        'employee_id': user.employee_id
                    })
            
            # Update UI on main thread
            QTimer.singleShot(0, lambda: self._update_users_ui(users, user_list_data))
            logger.info(f"Loaded {len(users)} users")
        except Exception as e:
            logger.error(f"Error loading users: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load users: {str(e)}")
    
    def load_results(self):
        """Load test results from database (synchronous)"""
        if not self.database:
            return
        
        try:
            # Get admin user
            admin_user = self.database.get_user_by_id(self.admin_id)
            if not admin_user:
                return
            
            # Get filter params
            filter_params = self.results_panel.get_filter_params()
            
            # Load results (synchronous)
            results = self.database.get_test_results_by_admin(
                admin_id=admin_user.id,
                start_date=filter_params.get('start_date'),
                end_date=filter_params.get('end_date')
            )
            
            # Apply user filter if specified
            if filter_params.get('user'):
                user_emp_id = filter_params['user'].split('(')[-1].rstrip(')')
                results = [r for r in results if r.get('employee_id') == user_emp_id]
            
            # Apply status filter if specified
            if filter_params.get('status'):
                results = [r for r in results if r.get('overall_status') == filter_params['status']]
            
            # Update UI on main thread
            QTimer.singleShot(0, lambda: self.results_panel.populate_table(results))
            logger.info(f"Loaded {len(results)} test results")
        except Exception as e:
            logger.error(f"Error loading results: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to load results: {str(e)}")
    
    def apply_results_filters(self):
        """Apply filters and reload results (synchronous)"""
        if not self.database:
            return
        
        self.load_results()
    
    def on_user_action(self, user_data: dict):
        """Handle user list action"""
        if user_data.get('action') == 'add':
            self.user_mgmt_panel.clear_form()
        else:
            self.user_mgmt_panel.load_user(user_data)
    
    def _update_users_ui(self, users, user_list_data):
        """Update users UI on main thread"""
        self.user_list_panel.clear_users()
        for user in users:
            if user.is_active:
                user_data = {
                    'employee_id': user.employee_id,
                    'name': user.name,
                    'role': user.role,
                    'id': user.id,
                    'admin_id': user.admin_id  # Include admin_id
                }
                self.user_list_panel.add_user(user_data)
        
        # Populate user filter
        self.results_panel.populate_user_filter(user_list_data)
    
    def on_save_user(self, user_data: dict):
        """Handle save user request (synchronous)"""
        if not self.database:
            QMessageBox.warning(self, "Error", "Database not available")
            return
        
        # Call synchronous save
        self._save_user_sync(user_data)
    
    def _save_user_sync(self, user_data: dict):
        """Save user implementation (synchronous)"""
        try:
            # Get admin user for admin_id
            admin_user = self.database.get_user_by_id(self.admin_id)
            admin_db_id = admin_user.id if admin_user else None
            
            employee_id = user_data.get('employee_id')
            name = user_data.get('name')
            password = user_data.get('password')
            
            # Check if updating or creating
            if employee_id:
                existing_user = self.database.get_user_by_id(employee_id)
            else:
                existing_user = None
            
            if existing_user:
                # Enforce that this admin can only modify their own users
                if existing_user.admin_id and admin_db_id and existing_user.admin_id != admin_db_id:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Access Denied", "You can only modify users that you created.")
                    return
                # Update existing user
                # Password is always employee_id + name for users
                updated_password = f"{employee_id}{name}"
                
                success = self.database.update_user(
                    employee_id=employee_id,
                    name=name,
                    password=updated_password
                )
                if success:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.information(self, "Success", f"User {name} updated successfully")
                    self.load_users()  # Synchronous
                    self.user_mgmt_panel.clear_form()
                else:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Error", "Failed to update user")
            else:
                # Create new user - auto-generate employee ID
                new_employee_id = self.database.generate_next_employee_id("USR")
                
                # Password is automatically employee_id + name
                auto_password = f"{new_employee_id}{name}"
                
                new_user = self.database.create_user(
                    employee_id=new_employee_id,
                    name=name,
                    password=auto_password,
                    role='user',
                    admin_id=admin_db_id
                )
                if new_user:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.information(
                        self, 
                        "User Created", 
                        f"User created successfully!\n\n"
                        f"Employee ID: {new_employee_id}\n"
                        f"Name: {name}\n"
                        f"Password: {new_employee_id}{name}\n\n"
                        f"Share these credentials with the user."
                    )
                    self.load_users()  # Synchronous
                    self.user_mgmt_panel.clear_form()
                else:
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Error", "User creation failed")
        except Exception as e:
            logger.error(f"Error saving user: {e}", exc_info=True)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to save user: {str(e)}")
    
    def on_delete_user(self, employee_id: str):
        """Handle delete user request (synchronous)"""
        if not self.database:
            return
        
        # Call synchronous delete
        self._delete_user_sync(employee_id)
    
    def _delete_user_sync(self, employee_id: str):
        """Delete user implementation (synchronous)"""
        try:
            # Verify ownership
            admin_user = self.database.get_user_by_id(self.admin_id)
            admin_db_id = admin_user.id if admin_user else None
            target_user = self.database.get_user_by_id(employee_id)
            if target_user and admin_db_id and target_user.admin_id != admin_db_id:
                QMessageBox.warning(self, "Access Denied", "You can only delete users that you created.")
                return
            
            success = self.database.delete_user(employee_id)
            if success:
                QMessageBox.information(self, "Success", f"User {employee_id} deleted")
                self.load_users()  # Synchronous
                self.user_mgmt_panel.clear_form()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete user")
        except Exception as e:
            logger.error(f"Error deleting user: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to delete user: {str(e)}")
    
    def on_export(self, format_type: str):
        """Handle export request"""
        if format_type == 'csv':
            self.export_to_csv()
    
    def export_to_csv(self):
        """Export results to CSV"""
        results = self.results_panel.get_all_results()
        
        if not results:
            QMessageBox.warning(self, "No Data", "No results to export")
            return
        
        # Get save location
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "test_results.csv", "CSV Files (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['User', 'Employee ID', 'Camera Serial', 'LED', 'IRLED', 'IRCUT', 'Speaker', 'Date']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for result in results:
                    writer.writerow({
                        'User': result.get('user', ''),
                        'Employee ID': result.get('employee_id', ''),
                        'Camera Serial': result.get('camera_serial', ''),
                        'LED': result.get('led', ''),
                        'IRLED': result.get('irled', ''),
                        'IRCUT': result.get('ircut', ''),
                        'Speaker': result.get('speaker', ''),
                        'Date': result.get('date', '')
                    })
            
            QMessageBox.information(self, "Success", f"Results exported to {file_path}")
            logger.info(f"Exported {len(results)} results to {file_path}")
        except Exception as e:
            logger.error(f"Error exporting CSV: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to export CSV: {str(e)}")
