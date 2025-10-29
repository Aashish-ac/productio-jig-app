"""
Admin Dashboard for User Management and Result Tracking
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QLineEdit, QComboBox, QHeaderView,
    QMessageBox, QListWidget, QSplitter, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class AdminDashboard(QWidget):
    """Admin dashboard for user management and result tracking"""
    
    user_selected = pyqtSignal(dict)  # Emits user data
    create_user_requested = pyqtSignal(dict)  # Emits new user data
    
    def __init__(self, admin_id: str, admin_name: str):
        super().__init__()
        self.admin_id = admin_id
        self.admin_name = admin_name
        self.users = []  # Will be populated from database
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel(f"👤 Admin Dashboard - {self.admin_name}")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4;")
        header_layout.addWidget(header_label)
        
        header_layout.addStretch()
        
        # Admin badge
        admin_badge = QLabel("🔑 ADMIN MODE")
        admin_badge.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #4caf50; "
            "background-color: #2d4a2d; padding: 8px 16px; border-radius: 5px;"
        )
        header_layout.addWidget(admin_badge)
        
        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        header_widget.setStyleSheet("background-color: #252526; border-radius: 10px; padding: 15px;")
        layout.addWidget(header_widget)
        
        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: User list
        self.create_user_list_panel(splitter)
        
        # Right panel: User management + Results
        self.create_main_content_panel(splitter)
        
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
        self.setLayout(layout)
    
    def create_user_list_panel(self, parent_splitter):
        """Create user list on left"""
        user_panel = QWidget()
        user_panel.setMinimumWidth(250)
        user_panel.setMaximumWidth(300)
        
        user_layout = QVBoxLayout()
        user_layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("👥 Users")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #fff; margin-bottom: 10px;")
        user_layout.addWidget(title)
        
        # User list
        self.user_list = QListWidget()
        self.user_list.setStyleSheet(self.get_list_style())
        self.user_list.itemClicked.connect(self.on_user_selected)
        user_layout.addWidget(self.user_list)
        
        # Add button
        add_user_btn = QPushButton("➕ Add User")
        add_user_btn.setStyleSheet(self.get_button_style("#4caf50"))
        add_user_btn.clicked.connect(self.show_add_user_dialog)
        user_layout.addWidget(add_user_btn)
        
        user_panel.setLayout(user_layout)
        parent_splitter.addWidget(user_panel)
        
        # Populate with demo users
        self.populate_demo_users()
    
    def create_main_content_panel(self, parent_splitter):
        """Create main content area"""
        main_panel = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Create sections in scrollable area
        scroll_area = self.create_scrollable_area()
        
        # User management panel
        self.create_user_management_panel(scroll_area)
        
        # Results panel
        self.create_results_panel(scroll_area)
        
        main_layout.addWidget(scroll_area)
        main_panel.setLayout(main_layout)
        parent_splitter.addWidget(main_panel)
    
    def create_scrollable_area(self):
        """Create scrollable content area"""
        # For now, just a regular widget
        # In production, use QScrollArea
        return QWidget()
    
    def create_user_management_panel(self, parent_widget):
        """Create user creation/editing panel"""
        # This will be a group box with form
        pass  # Will implement below
    
    def create_results_panel(self, parent_widget):
        """Create test results tracking panel"""
        # Results table
        results_frame = QFrame()
        results_frame.setStyleSheet("background-color: #252526; border-radius: 10px; padding: 15px;")
        results_layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("📊 Test Results")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #0078d4;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Filter controls
        filter_layout = QHBoxLayout()
        self.user_filter = QComboBox()
        self.user_filter.setPlaceholderText("Filter by user...")
        self.user_filter.setStyleSheet("padding: 6px; border-radius: 5px;")
        filter_layout.addWidget(QLabel("User:"))
        filter_layout.addWidget(self.user_filter)
        
        self.date_filter = QLineEdit()
        self.date_filter.setPlaceholderText("Filter by date...")
        self.date_filter.setStyleSheet("padding: 6px; border-radius: 5px;")
        filter_layout.addWidget(QLabel("Date:"))
        filter_layout.addWidget(self.date_filter)
        
        header_layout.addLayout(filter_layout)
        results_layout.addLayout(header_layout)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "User", "Camera Serial", "LED", "IRLED", "IRCUT", "Speaker", "Date"
        ])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setStyleSheet(self.get_table_style())
        self.results_table.setMaximumHeight(400)
        results_layout.addWidget(self.results_table)
        
        results_frame.setLayout(results_layout)
    
    def show_add_user_dialog(self):
        """Show dialog to add new user"""
        dialog = QWidget()
        dialog.setWindowTitle("Add User")
        dialog.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Form
        form_group = QGroupBox("User Information")
        form_layout = QFormLayout()
        
        # Employee ID
        self.new_user_id = QLineEdit()
        self.new_user_id.setPlaceholderText("Enter employee ID")
        form_layout.addRow("Employee ID:", self.new_user_id)
        
        # Name
        self.new_user_name = QLineEdit()
        self.new_user_name.setPlaceholderText("Enter name")
        form_layout.addRow("Name:", self.new_user_name)
        
        # Password
        self.new_user_password = QLineEdit()
        self.new_user_password.setPlaceholderText("Enter password")
        self.new_user_password.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Password:", self.new_user_password)
        
        # Role (readonly - always User for admin-created accounts)
        self.new_user_role = QLabel("user")
        form_layout.addRow("Role:", self.new_user_role)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        create_btn = QPushButton("Create User")
        create_btn.setStyleSheet(self.get_button_style("#0078d4"))
        create_btn.clicked.connect(lambda: self.create_new_user(dialog))
        btn_layout.addWidget(create_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(self.get_button_style("#888"))
        cancel_btn.clicked.connect(dialog.close)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        dialog.setLayout(layout)
        dialog.show()
    
    def create_new_user(self, dialog):
        """Create new user"""
        employee_id = self.new_user_id.text().strip()
        name = self.new_user_name.text().strip()
        password = self.new_user_password.text().strip()
        
        if not employee_id or not name or not password:
            QMessageBox.warning(dialog, "Error", "Please fill all fields")
            return
        
        # Emit signal
        new_user = {
            'employee_id': employee_id,
            'name': name,
            'password': password,
            'role': 'user',
            'admin_id': self.admin_id
        }
        
        self.create_user_requested.emit(new_user)
        self.user_list.addItem(f"👤 {name} ({employee_id})")
        
        dialog.close()
        QMessageBox.information(self, "Success", f"User {name} created successfully!")
    
    def populate_demo_users(self):
        """Add demo users to list"""
        demo_users = [
            ("John Doe", "U001"),
            ("Jane Smith", "U002"),
            ("Bob Wilson", "U003"),
        ]
        
        for name, emp_id in demo_users:
            self.user_list.addItem(f"👤 {name} ({emp_id})")
    
    def on_user_selected(self, item):
        """Handle user selection"""
        text = item.text()
        # Extract user info from item text
        logger.info(f"User selected: {text}")
    
    def get_list_style(self):
        return """
            QListWidget {
                background-color: #252526;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #3d3d3d;
                color: #fff;
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
                border-radius: 5px;
                padding: 10px;
                color: white;
                font-weight: bold;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
        """
    
    def get_table_style(self):
        return """
            QTableWidget {
                background-color: #1e1e1e;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                gridline-color: #3d3d3d;
            }
            QTableWidget::item {
                padding: 5px;
                color: #fff;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #fff;
                padding: 8px;
                font-weight: bold;
            }
        """

