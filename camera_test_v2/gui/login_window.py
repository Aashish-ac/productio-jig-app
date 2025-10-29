"""
Clean Login Window with Proper Layout
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit,  
    QPushButton, QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
import logging

logger = logging.getLogger(__name__)


class LoginWindow(QWidget):
    """Professional login window with clean layout"""
    
    login_successful = pyqtSignal(str, str, str)  # employee_id, name, role
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera Test Tool - Login")
        self.setFixedSize(450, 600)
        self.init_ui()
        self.apply_stylesheet()
    
    def init_ui(self):
        """Build UI with proper spacing"""
        layout = QVBoxLayout()
        layout.setSpacing(0)  # We'll add manual spacing
        layout.setContentsMargins(40, 40, 40, 40)
        
        # ===== HEADER =====
        title = QLabel("🔐 Camera Test Tool")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #000; margin-bottom: 8px;")
        layout.addWidget(title)
        
        subtitle = QLabel("Production Testing Platform")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #888; font-size: 13px; margin-bottom: 40px;")
        layout.addWidget(subtitle)
        
        # ===== ROLE DROPDOWN =====
        role_label = QLabel("Role:")
        role_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #333; margin-top: 15px; margin-bottom: 8px;")
        layout.addWidget(role_label)
        
        self.role_combo = QComboBox()
        self.role_combo.addItems(["User", "Admin"])
        self.role_combo.setCurrentText("User")
        self.role_combo.setFixedHeight(48)
        layout.addWidget(self.role_combo)
        
        # ===== EMPLOYEE ID =====
        id_label = QLabel("Employee ID:")
        id_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #333; margin-top: 20px; margin-bottom: 8px;")
        layout.addWidget(id_label)
        
        self.employee_id_input = QLineEdit()
        self.employee_id_input.setPlaceholderText("Enter employee ID (e.g., EMP001)")
        self.employee_id_input.setFixedHeight(48)
        self.employee_id_input.returnPressed.connect(self.handle_login)
        layout.addWidget(self.employee_id_input)
        
        # ===== FULL NAME =====
        name_label = QLabel("Full Name:")
        name_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #333; margin-top: 20px; margin-bottom: 8px;")
        layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter your full name")
        self.name_input.setFixedHeight(48)
        self.name_input.returnPressed.connect(self.handle_login)
        layout.addWidget(self.name_input)
        
        # ===== SPACER =====
        layout.addSpacing(30)
        
        # ===== LOGIN BUTTON =====
        self.login_btn = QPushButton("Login")
        self.login_btn.setFixedHeight(52)
        self.login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_btn)
        
        # ===== PUSH TO BOTTOM =====
        layout.addStretch()
        
        # ===== FOOTER =====
        footer = QLabel("Version 2.0.0 | Powered by Actoan")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #aaa; font-size: 11px; margin-top: 20px;")
        layout.addWidget(footer)
        
        self.setLayout(layout)
    
    def apply_stylesheet(self):
        """Apply clean, modern stylesheet"""
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
            }
            
            QLabel {
                color: #000000;
                background: transparent;
            }
            
            QLineEdit {
                background-color: #f5f5f5;
                color: #000000;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 0 16px;
                font-size: 14px;
            }
            
            QLineEdit:focus {
                border: 2px solid #0078d4;
                background-color: #ffffff;
            }
            
            QLineEdit::placeholder {
                color: #999999;
            }
            
            QComboBox {
                background-color: #f5f5f5;
                color: #000000;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 0 16px;
                font-size: 14px;
            }
            
            QComboBox:focus {
                border: 2px solid #0078d4;
                background-color: #ffffff;
            }
            
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 30px;
                border: none;
            }
            
            QComboBox::down-arrow {
                image: none;
                border: none;
                width: 0px;
            }
            
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #000000;
                selection-background-color: #0078d4;
                selection-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
            }
            
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #005a9e;
            }
            
            QPushButton:pressed {
                background-color: #004578;
            }
        """)
    
    def handle_login(self):
        """Handle login submission"""
        employee_id = self.employee_id_input.text().strip()
        name = self.name_input.text().strip()
        role = self.role_combo.currentText().lower()
        
        # Validation
        if not employee_id:
            self.show_error("Please enter Employee ID")
            self.employee_id_input.setFocus()
            return
        
        if not name:
            self.show_error("Please enter Full Name")
            self.name_input.setFocus()
            return
        
        # Success
        logger.info(f"Login: {employee_id} ({name}) as {role}")
        self.login_successful.emit(employee_id, name, role)
        
        # Note: The success dialog will be replaced by navigation to main window
        # This emit will trigger on_login_success in app.py
        
    def show_error(self, message: str):
        """Show error dialog"""
        QMessageBox.warning(self, "Login Error", message)
        logger.warning(f"Login error: {message}")
