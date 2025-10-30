"""
Main application window with 3-panel layout - PRODUCTION READY
Professional UI with proper spacing, 16:9 video, and visible checkboxes
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QListWidget, QPushButton, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QTextEdit, QLineEdit, QSplitter, QScrollArea, QCheckBox, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QPointF
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QPainterPath
from PyQt6.QtWidgets import QStyleOptionButton, QStyle
import logging

# Import video streaming manager
from .video_stream import VideoStreamManager

logger = logging.getLogger(__name__)


class CheckBoxWithTick(QCheckBox):
    """Custom checkbox that shows a checkmark tick when checked"""
    
    def paintEvent(self, event):
        """Override paint event to draw custom checkmark"""
        # Call parent paint to handle text and basic styling
        super().paintEvent(event)
        
        # Draw checkmark if checked
        if self.isChecked():
            option = QStyleOptionButton()
            self.initStyleOption(option)
            
            # Get the style to calculate indicator rect
            style = self.style()
            indicator_rect = style.subElementRect(
                QStyle.SubElement.SE_CheckBoxIndicator, 
                option, 
                self
            )
            
            # Draw checkmark centered in indicator
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Calculate checkmark position (centered in indicator with padding)
            indicator_width = indicator_rect.width()
            indicator_height = indicator_rect.height()
            center_x = indicator_rect.center().x()
            center_y = indicator_rect.center().y()
            
            # Use 70% of indicator size for checkmark with padding
            check_size = min(indicator_width, indicator_height) * 0.7
            
            # Draw checkmark with white pen (thicker for better visibility)
            pen = QPen(QColor(255, 255, 255), 3.0, Qt.PenStyle.SolidLine, 
                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            
            # Draw traditional checkmark shape - classic "✓" form
            # Bottom left point
            x1 = center_x - check_size * 0.2
            y1 = center_y + check_size * 0.1
            
            # Middle/bend point (at center)
            x2 = center_x - check_size * 0.05
            y2 = center_y
            
            # Top right point
            x3 = center_x + check_size * 0.3
            y3 = center_y - check_size * 0.3
            
            # Draw the checkmark as a smooth connected path
            path = QPainterPath()
            path.moveTo(x1, y1)
            path.lineTo(x2, y2)
            path.lineTo(x3, y3)
            painter.drawPath(path)
            painter.end()


class HeaderBar(QWidget):
    """Top header bar with company name and user info - FIXED"""
    def __init__(self, user_name: str, employee_id: str, role: str):
        super().__init__()
        self.user_name = user_name
        self.employee_id = employee_id
        self.role = role
        self.admin_id_text = None
        self.on_logout_requested = None  # callback to be set by parent window
        self.init_ui()
    
    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 8, 20, 8)  # REDUCED from 15 to 8
        
        # User info on left
        self.user_info = QLabel(f"👤 {self.user_name} ({self.employee_id}) [{self.role.upper()}]")
        self.user_info.setStyleSheet("font-size: 13px; color: #fff;")  # REDUCED from 14px
        layout.addWidget(self.user_info)
        
        # Admin id label (hidden until set)
        self.admin_label = QLabel("")
        self.admin_label.setStyleSheet("font-size: 12px; color: #bbb; margin-left: 12px;")
        layout.addWidget(self.admin_label)
        
        # Spacer
        layout.addStretch()
        
        # Logout button
        logout_btn = QPushButton("Logout")
        logout_btn.setFixedHeight(28)
        logout_btn.setStyleSheet("QPushButton { background-color: #d9534f; color: #fff; border: none; padding: 6px 12px; border-radius: 4px; } QPushButton:hover { background-color: #c9302c; }")
        logout_btn.clicked.connect(self._handle_logout)
        layout.addWidget(logout_btn)
        
        # Company name on right - FIXED with word wrap
        company_name = QLabel("Actoan")
        company_name.setStyleSheet("font-size: 18px; font-weight: bold; color: #0078d4;")  # REDUCED from 20px
        company_name.setWordWrap(False)
        company_name.setMinimumWidth(100)  # Ensure enough space
        layout.addWidget(company_name, alignment=Qt.AlignmentFlag.AlignRight)
        
        self.setLayout(layout)
        self.setStyleSheet("background-color: #1e1e1e; border-bottom: 1px solid #3d3d3d;")  # REDUCED border
        self.setFixedHeight(40)  # FIXED height to prevent expansion
    
    def _handle_logout(self):
        if callable(self.on_logout_requested):
            self.on_logout_requested()
    
    def set_admin_id(self, admin_employee_id: str):
        """Show admin employee ID (creator of this user)"""
        if admin_employee_id:
            self.admin_label.setText(f"Admin: {admin_employee_id}")
        else:
            self.admin_label.setText("")


class CameraListWidget(QWidget):
    """Left panel: Camera list with connection status - FIXED SPACING"""
    camera_selected = pyqtSignal(str)  # Emits camera serial number
    camera_add_requested = pyqtSignal(str, str)  # Emits (ip, serial)
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)  # REDUCED from 15
        layout.setSpacing(8)  # REDUCED from default
        
        # Title
        title = QLabel("📹 Cameras")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #fff; margin-bottom: 5px;")  # REDUCED
        layout.addWidget(title)
        
        # Add Camera section - COMPACT
        add_frame = QFrame()
        add_frame.setStyleSheet("background-color: #252526; border-radius: 5px; padding: 8px;")  # REDUCED from 12px
        add_layout = QVBoxLayout()
        add_layout.setSpacing(6)  # REDUCED spacing
        
        # IP Input
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Camera IP (e.g., 192.168.1.100)")
        self.ip_input.setStyleSheet("padding: 8px; border-radius: 4px;")  # REDUCED from 10px
        add_layout.addWidget(self.ip_input)
        
        # Serial Input
        self.serial_input = QLineEdit()
        self.serial_input.setPlaceholderText("Serial (e.g., CAM001)")
        self.serial_input.setStyleSheet("padding: 8px; border-radius: 4px;")  # REDUCED from 10px
        add_layout.addWidget(self.serial_input)
        
        # Add button
        self.add_btn = QPushButton("➕ Add Camera")
        self.add_btn.setStyleSheet(
            "background-color: #4caf50; color: white; border: none; padding: 8px; "  # REDUCED from 10px
            "border-radius: 4px; font-weight: bold; font-size: 12px;"  # REDUCED from 13px
        )
        self.add_btn.clicked.connect(self.on_add_camera_clicked)
        add_layout.addWidget(self.add_btn)
        
        add_frame.setLayout(add_layout)
        layout.addWidget(add_frame)
        layout.addSpacing(8)  # REDUCED from 15
        
        # Camera list
        self.camera_list = QListWidget()
        self.camera_list.setStyleSheet(self.get_list_style())
        self.camera_list.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.camera_list)
        
        self.setLayout(layout)
    
    def get_list_style(self):
        return """
            QListWidget {
                background-color: #252526;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                outline: none;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #3d3d3d;
                color: #fff;
                font-size: 12px;
            }
            QListWidget::item:hover {
                background-color: #2d2d2d;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
            }
        """
    
    def on_item_clicked(self, item):
        self.camera_selected.emit(item.text())
    
    def add_camera(self, serial: str, status: str = "disconnected"):
        status_icons = {
            "connected": "🟢",
            "disconnected": "🔴",
            "testing": "🟡",
            "error": "⚪"
        }
        icon = status_icons.get(status, "⚪")
        self.camera_list.addItem(f"{icon} {serial}")
    
    def update_camera_status(self, serial: str, status: str):
        for i in range(self.camera_list.count()):
            item = self.camera_list.item(i)
            if serial in item.text():
                status_icons = {"connected": "🟢", "disconnected": "🔴", "testing": "🟡", "error": "⚪"}
                icon = status_icons.get(status, "⚪")
                item.setText(f"{icon} {serial}")
                break
    
    def on_add_camera_clicked(self):
        ip = self.ip_input.text().strip()
        serial = self.serial_input.text().strip()
        if not ip or not serial:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Invalid Input", "Please enter both IP and Serial number")
            return
        self.camera_add_requested.emit(ip, serial)
        self.ip_input.clear()
        self.serial_input.clear()


class MainContentPanel(QWidget):
    """Center panel: Video, Tests, Results - FIXED SPACING"""
    def __init__(self, employee_id: str, employee_name: str, role: str):
        super().__init__()
        self.employee_id = employee_id
        self.employee_name = employee_name
        self.role = role
        self.current_camera = None
        self.init_ui()
    
    def init_ui(self):
        # Use scroll area for entire content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #1e1e1e; }")
        
        content = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)  # REDUCED from 20
        layout.setContentsMargins(15, 10, 15, 10)  # REDUCED from 20
        
        # Video Panel
        self.create_video_panel(layout)
        
        # Test Control Panel
        self.create_test_panel(layout)
        
        # Results Panel
        self.create_results_panel(layout)
        
        content.setLayout(layout)
        scroll.setWidget(content)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)
    
    def create_video_panel(self, parent_layout):
        """Create 16:9 video panel - COMPACT"""
        frame = QFrame()
        frame.setStyleSheet("background-color: #252526; border-radius: 6px; padding: 10px;")  # REDUCED from 15px
        frame_layout = QVBoxLayout()
        frame_layout.setSpacing(8)  # REDUCED from 12
        
        title = QLabel("📹 Camera Live View")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0078d4;")  # REDUCED from 16px
        frame_layout.addWidget(title)
        
        # Fixed 16:9 aspect ratio container
        video_container = QFrame()
        video_container.setStyleSheet("background-color: #000000; border: 2px solid #3d3d3d; border-radius: 5px;")
        video_container.setFixedHeight(405)  # 720 * (9/16) = 405
        video_container.setMinimumWidth(720)
        
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_label = QLabel("📺 Select a camera to view stream")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: #000000; color: #888; font-size: 13px;")  # REDUCED from 14px
        self.video_label.setScaledContents(False)
        
        container_layout.addWidget(self.video_label)
        video_container.setLayout(container_layout)
        frame_layout.addWidget(video_container)
        
        # Video controls - COMPACT
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)  # REDUCED from 10
        
        self.start_stream_btn = QPushButton("▶ Start Stream")
        self.start_stream_btn.setStyleSheet(self.get_button_style("#4caf50"))
        self.start_stream_btn.setMinimumWidth(110)  # REDUCED from 120
        self.start_stream_btn.setFixedHeight(32)  # Fixed height
        controls_layout.addWidget(self.start_stream_btn)
        
        self.stop_stream_btn = QPushButton("⏹ Stop")
        self.stop_stream_btn.setEnabled(False)
        self.stop_stream_btn.setStyleSheet(self.get_button_style("#d32f2f"))
        self.stop_stream_btn.setMinimumWidth(90)  # REDUCED from 100
        self.stop_stream_btn.setFixedHeight(32)
        controls_layout.addWidget(self.stop_stream_btn)
        
        controls_layout.addStretch()
        
        self.rtsp_url_input = QLineEdit()
        self.rtsp_url_input.setPlaceholderText("RTSP URL (e.g., rtsp://192.168.2.2/main)")
        self.rtsp_url_input.setStyleSheet("padding: 8px; border-radius: 4px; min-width: 350px;")  # REDUCED from 10px
        self.rtsp_url_input.setFixedHeight(32)
        controls_layout.addWidget(self.rtsp_url_input)
        
        frame_layout.addLayout(controls_layout)
        frame.setLayout(frame_layout)
        parent_layout.addWidget(frame)
        
        # Initialize video manager
        self.video_stream_manager = VideoStreamManager(self.video_label)
        self.start_stream_btn.clicked.connect(self.start_video_stream)
        self.stop_stream_btn.clicked.connect(self.stop_video_stream)
    
    def start_video_stream(self):
        rtsp_url = self.rtsp_url_input.text().strip()
        if not rtsp_url:
            return
        success = self.video_stream_manager.start_stream(rtsp_url)
        if success:
            self.start_stream_btn.setEnabled(False)
            self.stop_stream_btn.setEnabled(True)
            self.rtsp_url_input.setEnabled(False)
    
    def stop_video_stream(self):
        self.video_stream_manager.stop_stream()
        self.start_stream_btn.setEnabled(True)
        self.stop_stream_btn.setEnabled(False)
        self.rtsp_url_input.setEnabled(True)
    
    def create_test_panel(self, parent_layout):
        """Create test control panel with visible checkboxes - COMPACT"""
        frame = QFrame()
        frame.setStyleSheet("background-color: #252526; border-radius: 6px; padding: 10px;")  # REDUCED from 15px
        frame_layout = QVBoxLayout()
        frame_layout.setSpacing(8)  # REDUCED from 12
        
        title = QLabel("🧪 Test Control Panel")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0078d4;")  # REDUCED from 16px
        frame_layout.addWidget(title)
        
        # 2x2 grid with bright checkboxes - COMPACT
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)  # REDUCED from 15
        
        # Bright checkbox style for dark theme with checkmark
        checkbox_style = """
            QCheckBox {
                color: #ffffff;
                font-size: 12px;
                font-weight: bold;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #0078d4;
                border-radius: 4px;
                background-color: #1e1e1e;
            }
            QCheckBox::indicator:checked {
                background-color: #4caf50;
                border-color: #4caf50;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #5cbf60;
                border-color: #5cbf60;
            }
            QCheckBox::indicator:hover {
                border-color: #1e90ff;
                background-color: #2d2d2d;
            }
        """
        
        # Row 1
        self.led_btn = QPushButton("💡 LED Test")
        self.led_btn.setMinimumSize(130, 38)  # REDUCED from 140x45
        self.led_btn.setStyleSheet(self.get_button_style("#4caf50"))
        grid_layout.addWidget(self.led_btn, 0, 0)
        
        self.led_pass_checkbox = CheckBoxWithTick("✓ Pass")
        self.led_pass_checkbox.setStyleSheet(checkbox_style)
        grid_layout.addWidget(self.led_pass_checkbox, 0, 1)
        
        self.irled_btn = QPushButton("🔴 IRLED Test")
        self.irled_btn.setMinimumSize(130, 38)  # REDUCED
        self.irled_btn.setStyleSheet(self.get_button_style("#4caf50"))
        grid_layout.addWidget(self.irled_btn, 0, 2)
        
        self.irled_pass_checkbox = CheckBoxWithTick("✓ Pass")
        self.irled_pass_checkbox.setStyleSheet(checkbox_style)
        grid_layout.addWidget(self.irled_pass_checkbox, 0, 3)
        
        # Row 2
        self.ircut_btn = QPushButton("🔄 IRCUT Test")
        self.ircut_btn.setMinimumSize(130, 38)  # REDUCED
        self.ircut_btn.setStyleSheet(self.get_button_style("#4caf50"))
        grid_layout.addWidget(self.ircut_btn, 1, 0)
        
        self.ircut_pass_checkbox = CheckBoxWithTick("✓ Pass")
        self.ircut_pass_checkbox.setStyleSheet(checkbox_style)
        grid_layout.addWidget(self.ircut_pass_checkbox, 1, 1)
        
        self.speaker_btn = QPushButton("🔊 Speaker Test")
        self.speaker_btn.setMinimumSize(130, 38)  # REDUCED
        self.speaker_btn.setStyleSheet(self.get_button_style("#4caf50"))
        grid_layout.addWidget(self.speaker_btn, 1, 2)
        
        self.speaker_pass_checkbox = CheckBoxWithTick("✓ Pass")
        self.speaker_pass_checkbox.setStyleSheet(checkbox_style)
        grid_layout.addWidget(self.speaker_pass_checkbox, 1, 3)
        
        frame_layout.addLayout(grid_layout)
        
        # Camera status
        self.camera_status_label = QLabel("Select a camera to begin testing")
        self.camera_status_label.setStyleSheet("color: #a8a8a8; font-size: 12px; margin-top: 6px;")  # REDUCED
        frame_layout.addWidget(self.camera_status_label)
        
        self.test_checkboxes = {
            "led_test": self.led_pass_checkbox,
            "irled_test": self.irled_pass_checkbox,
            "ircut_test": self.ircut_pass_checkbox,
            "speaker_test": self.speaker_pass_checkbox
        }
        
        frame.setLayout(frame_layout)
        parent_layout.addWidget(frame)
    
    def create_results_panel(self, parent_layout):
        """Create scrollable results table - COMPACT"""
        frame = QFrame()
        frame.setStyleSheet("background-color: #252526; border-radius: 6px; padding: 10px;")  # REDUCED from 15px
        frame_layout = QVBoxLayout()
        frame_layout.setSpacing(8)  # REDUCED from 12
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("📊 Test Results")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #0078d4;")  # REDUCED from 16px
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.setStyleSheet(self.get_button_style("#666"))
        self.clear_btn.setMinimumWidth(90)  # REDUCED from 100
        self.clear_btn.setFixedHeight(32)
        header_layout.addWidget(self.clear_btn)
        
        self.save_btn = QPushButton("💾 Save Checked Results")
        self.save_btn.setStyleSheet(self.get_button_style("#0078d4"))
        self.save_btn.setMinimumWidth(170)  # REDUCED from 180
        self.save_btn.setFixedHeight(32)
        header_layout.addWidget(self.save_btn)
        
        frame_layout.addLayout(header_layout)
        
        # Results table with proper sizing
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Time", "Test", "Command", "Status", "Output", "Operator"
        ])
        self.results_table.setStyleSheet(self.get_table_style())
        self.results_table.setMinimumHeight(250)  # REDUCED from 280
        self.results_table.setMaximumHeight(400)  # REDUCED from 450
        
        # Column widths
        self.results_table.setColumnWidth(0, 80)
        self.results_table.setColumnWidth(1, 100)
        self.results_table.setColumnWidth(2, 200)
        self.results_table.setColumnWidth(3, 100)
        self.results_table.setColumnWidth(4, 250)
        self.results_table.setColumnWidth(5, 100)
        
        self.results_table.setAlternatingRowColors(True)
        self.results_table.verticalHeader().setVisible(False)
        
        frame_layout.addWidget(self.results_table)
        frame.setLayout(frame_layout)
        parent_layout.addWidget(frame)
    
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
                background-color: {self.darken_color(color)};
            }}
            QPushButton:disabled {{
                background-color: #555;
                color: #888;
            }}
        """
    
    def darken_color(self, hex_color: str) -> str:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r, g, b = max(0, r-20), max(0, g-20), max(0, b-20)
        return f"#{r:02x}{g:02x}{b:02x}"
    
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
    
    def update_camera(self, serial: str):
        self.current_camera = serial
        logger.info(f"Selected camera: {serial}")
        if hasattr(self, 'camera_status_label'):
            clean_serial = serial.split()[-1] if ' ' in serial else serial
            self.camera_status_label.setText(f"🟢 {clean_serial} • Telnet: Connected")
    
    def update_camera_status(self, serial: str, status: str):
        if hasattr(self, 'camera_status_label'):
            clean_serial = serial.split()[-1] if ' ' in serial else serial
            status_icon = "🟢" if status == "connected" else "🔴" if status == "error" else "🟡"
            self.camera_status_label.setText(f"{status_icon} {clean_serial} • Telnet: {status.capitalize()}")


class CameraTestMainWindow(QMainWindow):
    """Main application window - FIXED"""
    def __init__(self, employee_id: str, employee_name: str, role: str):
        super().__init__()
        self.employee_id = employee_id
        self.employee_name = employee_name
        self.role = role
        self.setWindowTitle("Camera Test Tool V2 - Production Edition")
        self.setMinimumSize(1500, 900)  # REDUCED from 950
        self.setStyleSheet("background-color: #1e1e1e; color: #fff;")
        self.telnet_pool = None
        self.websocket_manager = None
        self.init_ui()
    
    def init_ui(self):
        self.header_bar = HeaderBar(self.employee_name, self.employee_id, self.role)
        # Wire logout
        def do_logout():
            if hasattr(self, '_parent_app') and self._parent_app:
                self._parent_app.logout()
        self.header_bar.on_logout_requested = do_logout
        
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.header_bar)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.camera_list_panel = CameraListWidget()
        self.camera_list_panel.setMinimumWidth(250)  # REDUCED from 260
        self.camera_list_panel.setMaximumWidth(280)  # REDUCED from 300
        self.camera_list_panel.camera_selected.connect(self.on_camera_selected)
        self.camera_list_panel.camera_add_requested.connect(self.on_add_camera_requested)
        splitter.addWidget(self.camera_list_panel)
        
        self.main_content_panel = MainContentPanel(self.employee_id, self.employee_name, self.role)
        splitter.addWidget(self.main_content_panel)
        
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
    
    @pyqtSlot(str, str)
    def on_add_camera_requested(self, ip: str, serial: str):
        logger.info(f"Add camera request: {serial} at {ip}")
        self.camera_list_panel.add_camera(serial, "disconnected")
        if hasattr(self, '_parent_app') and self._parent_app:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._call_async_method(ip, serial))
    
    def _call_async_method(self, ip: str, serial: str):
        if hasattr(self, '_parent_app') and self._parent_app:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._parent_app.handle_add_camera(ip, serial))
                else:
                    asyncio.run(self._parent_app.handle_add_camera(ip, serial))
            except Exception as e:
                logger.error(f"Error calling async method: {e}")
    
    @pyqtSlot(str)
    def on_camera_selected(self, camera_serial: str):
        logger.info(f"Camera selected: {camera_serial}")
        if self.main_content_panel.video_stream_manager.is_streaming():
            self.main_content_panel.stop_video_stream()
        self.main_content_panel.update_camera(camera_serial)
        
        clean_serial = camera_serial.split()[-1] if ' ' in camera_serial else camera_serial
        if self.telnet_pool and clean_serial in self.telnet_pool.sessions:
            session = self.telnet_pool.sessions[clean_serial]
            ip = session.ip
        else:
            ip = "192.168.2.2"
        
        self.main_content_panel.rtsp_url_input.setText(f"rtsp://{ip}/main")
        self.main_content_panel.update_camera_status(clean_serial, "connected")

    def set_admin_id(self, admin_employee_id: str):
        """Expose setter to update header with admin id"""
        if hasattr(self, 'header_bar') and self.header_bar:
            self.header_bar.set_admin_id(admin_employee_id)
