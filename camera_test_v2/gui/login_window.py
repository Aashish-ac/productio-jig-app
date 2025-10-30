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
    
    login_successful = pyqtSignal(str, str, str, str)  # employee_id, name, role, password (optional)
    
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
        
        # ===== PASSWORD =====
        password_label = QLabel("Password:")
        password_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #333; margin-top: 20px; margin-bottom: 8px;")
        layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password (for Admin) or leave blank (for User)")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedHeight(48)
        self.password_input.returnPressed.connect(self.handle_login)
        layout.addWidget(self.password_input)
        
        # Help text
        help_text = QLabel("Note: For Users, password is automatically Employee ID + Name")
        help_text.setStyleSheet("color: #666; font-size: 11px; margin-top: 5px; margin-bottom: 20px;")
        layout.addWidget(help_text)
        
        # Connect role change to update password placeholder
        self.role_combo.currentTextChanged.connect(self.on_role_changed)
        
        # ===== SPACER =====
        layout.addSpacing(20)
        
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
    
    def on_role_changed(self, role_text: str):
        """Update password field based on role"""
        if role_text.lower() == "admin":
            self.password_input.setPlaceholderText("Enter password (required for Admin)")
            self.password_input.setEnabled(True)
        else:
            self.password_input.setPlaceholderText("Leave blank - auto-generated from ID + Name")
            self.password_input.setText("")
            self.password_input.setEnabled(False)
    
    def handle_login(self):
        """Handle login submission - now with database verification"""
        employee_id = self.employee_id_input.text().strip()
        name = self.name_input.text().strip()
        role = self.role_combo.currentText().lower()
        password = self.password_input.text().strip() if self.password_input.isEnabled() else None
        
        # Validation
        if not employee_id:
            self.show_error("Please enter Employee ID")
            self.employee_id_input.setFocus()
            return
        
        if not name:
            self.show_error("Please enter Full Name")
            self.name_input.setFocus()
            return
        
        if role == "admin" and not password:
            self.show_error("Password is required for Admin login")
            self.password_input.setFocus()
            return
        
        # Emit signal - app.py will handle database authentication
        logger.info(f"Login attempt: {employee_id} ({name}) as {role}")
        self.login_successful.emit(employee_id, name, role, password)
        
    def show_error(self, message: str):
        """Show error dialog"""
        QMessageBox.warning(self, "Login Error", message)
        logger.warning(f"Login error: {message}")
