import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from pathlib import Path
import os
from datetime import datetime
import sys
import logging
from .styles import GUIStyles
from .video_stream import VideoStreamWindow
from ..utils.serial_handler import SerialHandler
from ..utils.database import DatabaseManager
from ..utils.config import Config
from .log_window import LogWindow

class StdoutRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def write(self, text):
        self.text_widget.insert(tk.END, text)
        self.text_widget.see(tk.END)
        self.stdout.write(text)

    def flush(self):
        self.stdout.flush()

class CameraTestGUI:
    def __init__(self, root, employee_id=None, employee_name=None):
        self.root = root
        self.employee_id = employee_id or "UNKNOWN"
        self.employee_name = employee_name or "Unknown User"
        
        self.root.title(self.get_window_title())
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        self.root.resizable(True, True)
        
        # Save original stdout before any redirection
        self.original_stdout = sys.stdout
        
        # Initialize configuration
        self.config = Config()
        
        # Initialize database
        project_root = Path(__file__).resolve().parent.parent.parent
        db_path = os.path.join(project_root, "data", "camera_tests.db")
        self.db = DatabaseManager(db_path)
        
        # Setup logging
        self.setup_logging()
        
        # Save employee to database
        self.db.add_employee(self.employee_id, self.employee_name)
        self.logger.info(f"Employee logged in: {self.employee_name} ({self.employee_id})")
        
        self.styles = GUIStyles()
        self.setup_window()
        self.setup_variables()
        self.create_main_layout()
        
        # Initialize video and serial after layout
        self.video_stream = VideoStreamWindow(self, self.video_frame)
        self.serial_handler = SerialHandler(self)
        self.create_widgets()
        
        # Setup keyboard shortcuts
        self.setup_keyboard_shortcuts()
        
        # Configure window to show
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)
        
        # Start polling serial RX queue after GUI is ready
        self.root.after(100, self._poll_serial_rx)

        self.test_results = {
            'led_test': 'NOT_TESTED',
            'irled_test': 'NOT_TESTED',
            'ircut_test': 'NOT_TESTED',
            'speaker_test': 'NOT_TESTED',
            'camera_serial': 'CAM001',  # You might want to make this configurable
            'notes': ''
        }
        
    def get_window_title(self):
        """Generate window title with employee info"""
        return f"[Camera] IP Camera Production Test Tool - {self.employee_name} ({self.employee_id or 'N/A'})"

    def update_window_title(self):
        """Update window title with current employee info"""
        self.root.title(self.get_window_title())

    def setup_window(self):
        """Configure main window with modern styling"""
        # Remove conflicting geometry call - window size already set in __init__
        self.root.resizable(True, True)
        
        # Apply styles
        self.styles.setup_styles()
        self.colors = self.styles.colors
        
        # Configure root
        self.root.configure(bg=self.colors['bg'])
    
    def setup_logging(self):
        """Setup file logging for audit trail"""
        log_dir = self.config.get_log_dir()
        log_file = log_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Session started - Employee: {self.employee_name} ({self.employee_id})")
    
    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.root.bind('<Control-s>', lambda e: self.save_test_results())
        self.root.bind('<Control-q>', lambda e: self.on_closing())
        self.root.bind('<Control-l>', lambda e: self.clear_logs())
        self.root.bind('<F5>', lambda e: self.toggle_connection())
    
    def setup_variables(self):
        """Initialize variables"""
        # Load from config
        default_port = self.config.get('serial_port', '/dev/tty.usbserial-0001')
        default_baud = self.config.get('baud_rate', '57600')
        
        self.port_var = tk.StringVar(value=default_port)
        self.baud_var = tk.StringVar(value=default_baud)
        self.status_var = tk.StringVar(value="Disconnected")
        self.camera_status_var = tk.StringVar(value="Waiting...")
        self.msg_count = 0
        self.autoscroll_var = tk.BooleanVar(value=True)
        
        # === NEW: Test verification checkboxes ===
        self.led_test_passed = tk.BooleanVar(value=False)
        self.irled_test_passed = tk.BooleanVar(value=False)
        self.ircut_test_passed = tk.BooleanVar(value=False)
        self.speaker_test_passed = tk.BooleanVar(value=False)
        
        # Camera serial number for tracking
        self.camera_serial_var = tk.StringVar(value="")
        
        # Update LED commands with correct shell commands
        # Ircut is handled from gpio's, leds are handled from pwm's
        self.command_map = {
            'LED_ON': 'echo 1 > /sys/devices/platform/soc/18820000.pwm/settings/pwm1/enable',
            'LED_OFF': 'echo 0 > /sys/devices/platform/soc/18820000.pwm/settings/pwm1/enable',
            'IRLED_ON': 'echo 1 > /sys/devices/platform/soc/18820000.pwm/settings/pwm3/enable',
            'IRLED_OFF': 'echo 0 > /sys/devices/platform/soc/18820000.pwm/settings/pwm3/enable',
            'IRCUT_ON': './sbin/control_gpio.sh ircut 1',
            'IRCUT_OFF': './sbin/control_gpio.sh ircut 0',
        }
        
        # Boot login variables
        self.boot_login_pending = False
        self.boot_login_after_ids = []
        self.boot_ready_marker = "Play streams from this server using the URL"
        self.boot_ready_delay_ms = 10000
        
    def create_main_layout(self):
        """Create main window layout with proper spacing and sizing"""
        # Set larger window size for better UX
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # Left panel with scrollbar - widened to accommodate scrollbar
        left_container = tk.Frame(self.root, bg=self.colors['bg'], width=335)
        left_container.pack(side='left', fill='y', padx=8, pady=8)
        left_container.pack_propagate(False)
        
        # Canvas for scrolling - width leaves room for scrollbar
        canvas = tk.Canvas(left_container, bg=self.colors['bg'], 
                          highlightthickness=0, width=305)
        canvas.pack(side="left", fill="both", expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        
        # Scrollable frame
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg'])
        
        # Create canvas window with proper width
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, 
                                            anchor="nw", width=305)
        
        # Configure scroll region update
        def _configure_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Update window width to match canvas width
            canvas.itemconfig(canvas_window, width=canvas.winfo_width())
        
        scrollable_frame.bind("<Configure>", _configure_scroll)
        canvas.bind("<Configure>", _configure_scroll)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Enable mouse wheel scrolling (cross-platform) - only when over left panel
        def _on_mousewheel(event):
            if left_container.winfo_containing(event.x_root, event.y_root):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _on_scroll(event):
            if left_container.winfo_containing(event.x_root, event.y_root):
                if event.num == 4:  # Linux scroll up
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:  # Linux scroll down
                    canvas.yview_scroll(1, "units")
        
        # Bind mousewheel only when mouse is over left panel
        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_scroll)
            canvas.bind_all("<Button-5>", _on_scroll)
        
        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")
        
        left_container.bind("<Enter>", _bind_mousewheel)
        left_container.bind("<Leave>", _unbind_mousewheel)
        
        # Store canvas reference for updating
        self.left_canvas = canvas
        
        # Make scrollable_frame the main left_frame
        self.left_frame = scrollable_frame
        
        # Right side container
        right_container = tk.Frame(self.root, bg=self.colors['bg'])
        right_container.pack(side='right', fill='both', expand=True, padx=8, pady=8)
        
        # === VIDEO SECTION ===
        # Video frame (top) - Gets majority of space
        video_container = ttk.Frame(right_container, style='Card.TFrame')
        video_container.pack(fill='both', expand=True, pady=(0, 8))
        
        # Video title bar
        video_title = tk.Frame(video_container, bg=self.colors['card_bg'], height=45)
        video_title.pack(fill='x')
        video_title.pack_propagate(False)
        
        tk.Label(video_title, text="📹 Camera Live View",
                bg=self.colors['card_bg'],
                fg=self.colors['text'],
                font=('Helvetica Neue', 12, 'bold')).pack(side='left', padx=15, pady=10)
        
        # Video display area
        self.video_frame = ttk.Frame(video_container)
        self.video_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # === TERMINAL LOG SECTION ===
        # Logs frame (bottom) - Fixed height for visibility
        logs_container = ttk.Frame(right_container, style='Card.TFrame')
        logs_container.pack(fill='x', pady=(8, 0))
        logs_container.pack_propagate(False)
        logs_container.configure(height=280)
        
        # Logs header
        logs_header = tk.Frame(logs_container, bg=self.colors['card_bg'], height=45)
        logs_header.pack(fill='x')
        logs_header.pack_propagate(False)
        
        tk.Label(logs_header, text="📋 Terminal Log",
                bg=self.colors['card_bg'],
                fg=self.colors['text'],
                font=('Helvetica Neue', 11, 'bold')).pack(side='left', padx=15, pady=10)
        
        # Logs controls
        ttk.Button(logs_header, text="Clear", 
                  command=self.clear_logs,
                  style='Modern.TButton').pack(side='right', padx=8)
        
        ttk.Button(logs_header, text="Save", 
                  command=self.save_logs,
                  style='Modern.TButton').pack(side='right')
        
        tk.Checkbutton(logs_header, text="Auto-scroll",
                       variable=self.autoscroll_var,
                       bg=self.colors['card_bg'],
                       fg=self.colors['text'],
                       selectcolor=self.colors['bg']).pack(side='right', padx=12, pady=10)
        
        # Logs text area - Fill remaining space
        self.logs_text = scrolledtext.ScrolledText(
            logs_container,
            bg=self.colors['bg'],
            fg=self.colors['text'],
            font=('Consolas', 9),
            wrap=tk.WORD)
        self.logs_text.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Configure text tags
        self.logs_text.tag_configure('sent', foreground='#87CEEB')
        self.logs_text.tag_configure('received', foreground='#98FB98')
        self.logs_text.tag_configure('status', foreground='#FFD700')
        self.logs_text.tag_configure('error', foreground='#FF6B6B')
        self.logs_text.tag_configure('ready', foreground='#FF69B4', font=('Consolas', 9, 'bold'))
        
        # Add initial log
        self.log_message("Terminal initialized - Ready", 'status')

    def create_widgets(self):
        """Create all GUI widgets"""
        # Title
        title_label = ttk.Label(self.left_frame, 
                               text="[Camera] Camera Test Tool",
                               style='Title.TLabel')
        title_label.pack(pady=(0, 20))
        
        # Connection Panel
        self.create_connection_panel()
        
        # Status Panel
        self.create_status_panel()
        
        # Control Panel
        self.create_control_panel()

    def create_connection_panel(self):
        """Create connection control panel with proper spacing"""
        conn_frame = ttk.Frame(self.left_frame, style='Card.TFrame', padding=12)
        conn_frame.pack(fill='x', pady=(0, 12))
        
        # Title
        ttk.Label(conn_frame, text="Connection", 
                 style='Title.TLabel').pack(anchor='w', pady=(0, 10))
        
        # Port selection - Full width
        port_label = tk.Label(conn_frame, text="Serial Port:",
                         bg=self.colors['card_bg'],
                         fg=self.colors['text'],
                         font=('Helvetica Neue', 10))
        port_label.pack(anchor='w', pady=(5, 2))
        
        # Populate with available ports
        available_ports = SerialHandler.get_available_ports()
        # Always include the default port if not in the list
        preferred = "/dev/tty.usbserial-0001"
        if preferred not in available_ports:
            available_ports.append(preferred)
        
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, 
                                      values=available_ports,
                                      state='readonly')
        self.port_combo.pack(fill='x', pady=(0, 8))
        
        # Set default selection
        if preferred in available_ports:
            self.port_var.set(preferred)
        elif available_ports:
            self.port_var.set(available_ports[0])
        
        # Baud selection - Full width
        baud_label = tk.Label(conn_frame, text="Baud Rate:",
                         bg=self.colors['card_bg'],
                         fg=self.colors['text'],
                         font=('Helvetica Neue', 10))
        baud_label.pack(anchor='w', pady=(5, 2))
        
        self.baud_combo = ttk.Combobox(conn_frame, textvariable=self.baud_var,
                                      values=["9600","19200","38400","57600","115200"],
                                      state='readonly')
        self.baud_combo.pack(fill='x', pady=(0, 10))
        
        # Connect button - Full width
        self.connect_btn = ttk.Button(conn_frame, text="⚡ Connect",
                                    command=self.toggle_connection,
                                    style='Success.TButton')
        self.connect_btn.pack(fill='x', ipady=6)

    def create_status_panel(self):
        """Create status display panel"""
        status_frame = ttk.Frame(self.left_frame, style='Card.TFrame', padding=15)
        status_frame.pack(fill='x', pady=(0, 15))
        
        ttk.Label(status_frame, text="[Status] Status", 
                 style='Title.TLabel').pack(anchor='w')
        
        # Connection status
        self.status_label = ttk.Label(status_frame, 
                                    textvariable=self.status_var)
        self.status_label.pack(fill='x', pady=5)
        
        # Employee info
        employee_info = tk.Label(status_frame,
                                text=f"👤 {self.employee_name}\nID: {self.employee_id}",
                                bg=self.colors['card_bg'],
                                fg=self.colors['text_secondary'],
                                font=('Helvetica Neue', 9),
                                justify='left')
        employee_info.pack(fill='x', pady=5)
        
        # Camera Serial input
        serial_label = tk.Label(status_frame,
                               text="Camera Serial:",
                               bg=self.colors['card_bg'],
                               fg=self.colors['text'],
                               font=('Helvetica Neue', 9))
        serial_label.pack(anchor='w', pady=(10, 2))
        
        self.camera_serial_entry = ttk.Entry(status_frame,
                                           textvariable=self.camera_serial_var,
                                           style='Form.TEntry')
        self.camera_serial_entry.pack(fill='x', pady=2)
        
        # === Save Results Button ===
        self.save_results_btn = ttk.Button(status_frame, 
                                          text="💾 Save Test Results",
                                          command=self.save_test_results,
                                          style='Success.TButton')
        self.save_results_btn.pack(fill='x', pady=(10, 0))
        
        # Add helpful label
        help_label = tk.Label(status_frame,
                             text="Click to save all test results",
                             bg=self.colors['card_bg'],
                             fg=self.colors['text_secondary'],
                             font=('Helvetica Neue', 8))
        help_label.pack(pady=(2, 0))
        
        # === View Results Button ===
        view_results_btn = ttk.Button(status_frame,
                                     text="📊 View All Results",
                                     command=self.open_results_viewer,
                                     style='Modern.TButton')
        view_results_btn.pack(fill='x', pady=(5, 0))

    # === NEW METHOD: Update button states based on test progression ===
    def update_test_states(self):
        """Enable/disable controls based on test completion and save results"""
        # Check if buttons exist before trying to configure them
        if not hasattr(self, 'irled_on_btn'):
            return
        
        # Update test results dictionary when checkboxes change
        self.test_results['led_test'] = 'PASS' if self.led_test_passed.get() else 'NOT_TESTED'
        self.test_results['irled_test'] = 'PASS' if self.irled_test_passed.get() else 'NOT_TESTED'
        self.test_results['ircut_test'] = 'PASS' if self.ircut_test_passed.get() else 'NOT_TESTED'
        self.test_results['speaker_test'] = 'PASS' if self.speaker_test_passed.get() else 'NOT_TESTED'
        
        # Update camera serial
        self.test_results['camera_serial'] = self.camera_serial_var.get()
        
        # Enable/disable next test controls based on progression
        ir_led_state = 'normal' if self.led_test_passed.get() else 'disabled'
        self.irled_on_btn.config(state=ir_led_state)
        self.irled_off_btn.config(state=ir_led_state)
        
        ircut_state = 'normal' if self.irled_test_passed.get() else 'disabled'
        self.ircut_on_btn.config(state=ircut_state)
        self.ircut_off_btn.config(state=ircut_state)
        
        speaker_state = 'normal' if self.ircut_test_passed.get() else 'disabled'
        self.speaker_test_btn.config(state=speaker_state)
        
        # Log progression
        if self.led_test_passed.get():
            self.log_message("✅ LED Test PASSED - IR LED unlocked", 'status')
        if self.irled_test_passed.get():
            self.log_message("✅ IR LED Test PASSED - IRCUT unlocked", 'status')
        if self.ircut_test_passed.get():
            self.log_message("✅ IRCUT Test PASSED - Speaker unlocked", 'status')
        if self.speaker_test_passed.get():
            self.log_message("✅ Speaker Test PASSED - All tests complete!", 'status')
        
        # Check if ready to save
        self.check_and_save_results()
    
    def check_and_save_results(self):
        """Check if all tests complete and prompt to save (only for all PASS)"""
        all_passed = (
            self.led_test_passed.get() and
            self.irled_test_passed.get() and
            self.ircut_test_passed.get() and
            self.speaker_test_passed.get()
        )
        
        if all_passed:
            # Get camera serial
            camera_serial = self.camera_serial_var.get().strip()
            if not camera_serial:
                # Don't auto-save if no serial, just prompt user
                return
            
            # Prompt to save (only once when all tests pass)
            if not hasattr(self, '_save_prompt_shown'):
                self._save_prompt_shown = True
                response = messagebox.askyesno(
                    "Save Test Results?",
                    f"All tests PASSED for camera {camera_serial}!\n\n"
                    f"Save results to database?"
                )
                
                if response:
                    self.save_test_results()
                else:
                    self._save_prompt_shown = False
        
        # Note: Manual save is always allowed via save button, even if some tests failed
    
    def reset_test_session(self):
        """Reset test session for next camera"""
        # Reset checkboxes
        self.led_test_passed.set(False)
        self.irled_test_passed.set(False)
        self.ircut_test_passed.set(False)
        self.speaker_test_passed.set(False)
        
        # Clear camera serial
        self.camera_serial_var.set("")
        
        # Reset prompt flag
        self._save_prompt_shown = False
        
        # Reset button states
        self.update_test_states()
        
        # Log reset
        self.log_message("=" * 60, 'status')
        self.log_message("✨ Ready for next camera test", 'status')
        self.log_message("=" * 60, 'status')

    def create_control_panel(self):
        """Create control panel with action buttons and test checkboxes"""
        control_frame = ttk.Frame(self.left_frame, style='Card.TFrame', padding=15)
        control_frame.pack(fill='x', pady=(0, 15))
        
        ttk.Label(control_frame, text="[Controls] Controls", 
                 style='Title.TLabel').pack(anchor='w')
        
        # Device controls grid
        controls_grid = ttk.Frame(control_frame)
        controls_grid.pack(fill='x', pady=5)

        # === LED Controls (Always enabled - first test) ===
        led_container = ttk.Frame(controls_grid)
        led_container.pack(fill='x', pady=2)
        
        led_frame = ttk.LabelFrame(led_container, text="LED", padding=5)
        led_frame.pack(side='left', fill='x', expand=True)
        
        self.led_on_btn = ttk.Button(led_frame, text="ON",
                  command=lambda: self.send_command('echo 1 > /sys/devices/platform/soc/18820000.pwm/settings/pwm1/enable'),
                  style='Success.TButton', width=8)
        self.led_on_btn.pack(side='left', padx=2)
        
        self.led_off_btn = ttk.Button(led_frame, text="OFF",
                  command=lambda: self.send_command('echo 0 > /sys/devices/platform/soc/18820000.pwm/settings/pwm1/enable'),
                  style='Danger.TButton', width=8)
        self.led_off_btn.pack(side='left', padx=2)
        
        # LED Test Checkbox
        led_check = tk.Checkbutton(led_container, text="✓ Pass",
                                   variable=self.led_test_passed,
                                   command=self.update_test_states,
                                   bg=self.colors['card_bg'],
                                   fg='#4CAF50',
                                   selectcolor=self.colors['bg'],
                                   font=('Helvetica Neue', 9, 'bold'))
        led_check.pack(side='right', padx=5)

        # === IR LED Controls (Disabled until LED test passes) ===
        irled_container = ttk.Frame(controls_grid)
        irled_container.pack(fill='x', pady=2)
        
        irled_frame = ttk.LabelFrame(irled_container, text="IR LED", padding=5)
        irled_frame.pack(side='left', fill='x', expand=True)
        
        self.irled_on_btn = ttk.Button(irled_frame, text="ON",
                  command=lambda: self.send_command("echo 1 > /sys/devices/platform/soc/18820000.pwm/settings/pwm3/enable"),
                  style='Success.TButton', width=8, state='disabled')
        self.irled_on_btn.pack(side='left', padx=2)
        
        self.irled_off_btn = ttk.Button(irled_frame, text="OFF",
                  command=lambda: self.send_command("echo 0 > /sys/devices/platform/soc/18820000.pwm/settings/pwm3/enable"),
                  style='Danger.TButton', width=8, state='disabled')
        self.irled_off_btn.pack(side='left', padx=2)
        
        # IR LED Test Checkbox
        irled_check = tk.Checkbutton(irled_container, text="✓ Pass",
                                     variable=self.irled_test_passed,
                                     command=self.update_test_states,
                                     bg=self.colors['card_bg'],
                                     fg='#4CAF50',
                                     selectcolor=self.colors['bg'],
                                     font=('Helvetica Neue', 9, 'bold'))
        irled_check.pack(side='right', padx=5)

        # === IRCUT Controls (Disabled until IR LED test passes) ===
        ircut_container = ttk.Frame(controls_grid)
        ircut_container.pack(fill='x', pady=2)
        
        ircut_frame = ttk.LabelFrame(ircut_container, text="IRCUT", padding=5)
        ircut_frame.pack(side='left', fill='x', expand=True)
        
        self.ircut_on_btn = ttk.Button(ircut_frame, text="ON",
                  command=lambda: self.send_command("./sbin/control_gpio.sh ircut 1"),
                  style='Success.TButton', width=8, state='disabled')
        self.ircut_on_btn.pack(side='left', padx=2)
        
        self.ircut_off_btn = ttk.Button(ircut_frame, text="OFF",
                  command=lambda: self.send_command("./sbin/control_gpio.sh ircut 0"),
                  style='Danger.TButton', width=8, state='disabled')
        self.ircut_off_btn.pack(side='left', padx=2)
        
        # IRCUT Test Checkbox
        ircut_check = tk.Checkbutton(ircut_container, text="✓ Pass",
                                     variable=self.ircut_test_passed,
                                     command=self.update_test_states,
                                     bg=self.colors['card_bg'],
                                     fg='#4CAF50',
                                     selectcolor=self.colors['bg'],
                                     font=('Helvetica Neue', 9, 'bold'))
        ircut_check.pack(side='right', padx=5)

        # === Speaker Test (Disabled until IRCUT test passes) ===
        speaker_container = ttk.Frame(controls_grid)
        speaker_container.pack(fill='x', pady=2)
        
        speaker_frame = ttk.LabelFrame(speaker_container, text="Speaker", padding=5)
        speaker_frame.pack(side='left', fill='x', expand=True)
        
        self.speaker_test_btn = ttk.Button(speaker_frame, text="Test Audio",
                  command=self.run_speaker_test,
                  style='Modern.TButton', width=16, state='disabled')
        self.speaker_test_btn.pack(side='left', padx=2)
        
        # Speaker Test Checkbox
        speaker_check = tk.Checkbutton(speaker_container, text="✓ Pass",
                                       variable=self.speaker_test_passed,
                                       command=self.update_test_states,
                                       bg=self.colors['card_bg'],
                                       fg='#4CAF50',
                                       selectcolor=self.colors['bg'],
                                       font=('Helvetica Neue', 9, 'bold'))
        speaker_check.pack(side='right', padx=5)

        # === Common controls (always enabled) ===
        common_frame = ttk.Frame(control_frame)
        common_frame.pack(fill='x', pady=10)
        
        ttk.Button(common_frame, text="[START] START",
                  command=lambda: self.send_command("start"),
                  style='Success.TButton', width=10).pack(side='left', padx=2)
        ttk.Button(common_frame, text="[STOP] STOP",
                  command=lambda: self.send_command("stop"),
                  style='Danger.TButton', width=10).pack(side='left', padx=2)
        ttk.Button(common_frame, text="[STATUS] STATUS",
                  command=lambda: self.send_command("ps"),
                  style='Modern.TButton', width=10).pack(side='left', padx=2)

    def show_terminal(self):
        """Show terminal window"""
        if not hasattr(self, 'log_window'):
            self.log_window = LogWindow(self)
        self.log_window.show_window()

    def toggle_connection(self):
        """Connect or disconnect from serial port"""
        if self.serial_handler.is_connected:
            try:
                self.serial_handler.disconnect()
                self.status_var.set("Disconnected")
                self.connect_btn.configure(text="⚡ Connect", style='Success.TButton')
            except Exception as e:
                messagebox.showerror("Error", str(e))
        else:
            try:
                port = self.port_var.get()
                if not port:
                    messagebox.showerror("Error", "Please select a port")
                    return
                
                self.serial_handler.connect(port, self.baud_var.get())
                self.status_var.set("Connected")
                self.connect_btn.configure(text="🔌 Disconnect", style='Danger.TButton')
            except Exception as e:
                messagebox.showerror("Connection Error", str(e))

    def send_command(self, command):
        """Send command to device"""
        try:
            self.serial_handler.send_command(command)
            # Note: command is already logged in serial_handler.send_command()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def process_serial_message(self, message):
        """Process received serial message"""
        self.log_message(f"📥 {message}", 'received')
        
        if "I AM READY" in message:
            self.camera_status_var.set("🟢 READY")
            self.camera_status_label.configure(fg=self.colors['success'])
        elif self.boot_ready_marker in message and not self.boot_login_pending:
            self.boot_login_pending = True
            self.log_message("Boot detected, scheduling login...", 'status')
            self.root.after(self.boot_ready_delay_ms, self._boot_send_root)

    def _poll_serial_rx(self):
        """Poll serial RX queue and display messages (called every 50ms)"""
        import queue
        try:
            while True:
                msg = self.serial_handler.rx_queue.get_nowait()
                self.process_received_message(msg)
        except queue.Empty:
            pass
        finally:
            # Re-schedule every 50ms
            self.root.after(50, self._poll_serial_rx)

    def schedule_login(self):
        """Schedule login sequence"""
        self.root.after(10000, lambda: self.send_command("root"))
        self.root.after(11000, lambda: self.send_command("cd /"))

    def on_closing(self):
        """Handle window closing"""
        try:
            # Restore original stdout
            sys.stdout = self.original_stdout
            
            # Clean up resources
            if hasattr(self, 'serial_handler'):
                self.serial_handler.disconnect()
            
            if hasattr(self, 'video_stream'):
                self.video_stream.stop_stream()
        except:
            pass
        finally:
            self.root.destroy()

    def run_speaker_test(self):
        """Run speaker test sequence"""
        if not self.serial_handler.is_connected:
            messagebox.showwarning("Warning", "Not connected to camera!")
            return
            
        self.send_command("killall capture") 
        self.root.after(5000, lambda: self.send_command("aplay -D hw:0,1 /overlay/test_saudio.wav")) # to check speaker we must have this test_saudio.wav file in our camera. We had it inside the overlay for testing.
                                                                                                    
    def run_mapped(self, key):
        """Execute mapped command with logging"""
        if not self.serial_handler.is_connected:
            messagebox.showwarning("Warning", "Not connected to camera!")
            return
            
        cmd = self.command_map.get(key)
        if not cmd:
            self.log_message(f"Unknown command key: {key}", 'error')
            return
            
        self.log_message(f"Executing {key}", 'status')
        self.send_command(cmd)

    def log_message(self, message, tag=''):
        """Add message to logs with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted_msg = f"[{timestamp}] {message}\n"
        
        # Write to main window logs
        if hasattr(self, 'logs_text') and self.logs_text is not None:
            try:
                self.logs_text.insert(tk.END, formatted_msg, tag)
                self.logs_text.see(tk.END)
            except Exception as e:
                sys.__stdout__.write(f"Log error (main): {e}\n{formatted_msg}")
        
        # Also write to separate log window if open
        if hasattr(self, 'log_window_ref') and self.log_window_ref is not None:
            if hasattr(self.log_window_ref, 'logs_text') and self.log_window_ref.logs_text is not None:
                try:
                    self.log_window_ref.logs_text.insert(tk.END, formatted_msg, tag)
                    if self.autoscroll_var.get():
                        self.log_window_ref.logs_text.see(tk.END)
                except Exception as e:
                    sys.__stdout__.write(f"Log error (window): {e}\n{formatted_msg}")
        
        self.msg_count += 1
        if hasattr(self, 'msg_counter_label'):
            self.msg_counter_label.configure(text=f"Messages: {self.msg_count}")
    
    def log_message_safe(self, message, tag=''):
        """Thread-safe wrapper for log_message - can be called from any thread"""
        try:
            self.root.after_idle(self.log_message, message, tag)
        except:
            # If root is not ready, just print to stdout
            sys.__stdout__.write(f"[THREAD] {message}\n")

    def clear_logs(self):
        """Clear the logs text area"""
        if hasattr(self, 'logs_text'):
            self.logs_text.delete(1.0, tk.END)

    def save_logs(self):
        """Save logs to a file"""
        logs = self.logs_text.get(1.0, tk.END).strip()
        if not logs:
            messagebox.showinfo("Info", "No logs to save")
            return
        
        file_path = tk.filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Logs As")
        
        if not file_path:
            return
        
        try:
            with open(file_path, "w") as file:
                file.write(logs)
            messagebox.showinfo("Success", "Logs saved successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save logs: {str(e)}")

    def process_received_message(self, message):
        """Process received serial message"""
        self.log_message(f"📥 {message}", 'received')
        
        if "I AM READY" in message:
            self.camera_status_var.set("🟢 READY")
            self.camera_status_label.configure(fg=self.colors['success'])
        elif self.boot_ready_marker in message and not self.boot_login_pending:
            self.boot_login_pending = True
            self.log_message("Boot detected, scheduling login...", 'status')
            self.root.after(self.boot_ready_delay_ms, self._boot_send_root)

    def _boot_send_root(self):
        """Send root command after boot delay"""
        self.send_command("root")
        self.send_command("cd /")

    def mark_test(self, test_name, result):
        """Mark a test as PASS/FAIL"""
        self.test_results[test_name] = result
        self.log_message(f"✓ Marked {test_name} as {result}", 'status')

    def save_test_results(self):
        """Save all test results to database"""
        if not hasattr(self, 'employee_id') or not self.employee_id:
            messagebox.showerror("Error", "No employee ID found!")
            return

        # Get camera serial from entry field
        camera_serial = self.camera_serial_var.get().strip()
        if not camera_serial:
            messagebox.showwarning("Warning", "Please enter Camera Serial Number")
            return

        # Save employee to database
        self.db.add_employee(self.employee_id, self.employee_name)

        # Prepare test data with proper PASS/FAIL status
        # Convert NOT_TESTED to FAIL and ensure all fields have values
        test_data = {
            'camera_serial': camera_serial,
            'led_test': 'PASS' if self.led_test_passed.get() else 'FAIL',
            'irled_test': 'PASS' if self.irled_test_passed.get() else 'FAIL',
            'ircut_test': 'PASS' if self.ircut_test_passed.get() else 'FAIL',
            'speaker_test': 'PASS' if self.speaker_test_passed.get() else 'FAIL',
            'notes': self.test_results.get('notes', '')
        }

        # Show confirmation dialog before saving
        passed_count = sum([1 for k, v in test_data.items() if k.endswith('_test') and v == 'PASS'])
        failed_count = sum([1 for k, v in test_data.items() if k.endswith('_test') and v == 'FAIL'])
        
        confirm_msg = (
            f"Save test results to database?\n\n"
            f"Camera Serial: {camera_serial}\n"
            f"Employee: {self.employee_name}\n\n"
            f"Tests Passed: {passed_count}/4\n"
            f"Tests Failed: {failed_count}/4"
        )
        
        response = messagebox.askyesno("Confirm Save", confirm_msg)
        
        if not response:
            return
        
        try:
            test_id = self.db.save_test_result(self.employee_id, test_data)
            if test_id:
                # Create detailed log message
                test_summary = ", ".join([f"{k}: {v}" for k, v in test_data.items() if k.endswith('_test')])
                self.log_message(f"✓ Test results saved (ID: {test_id}) - {test_summary}", 'status')
                self.logger.info(f"Test saved: Employee={self.employee_id}, Camera={camera_serial}, Results={test_data}")
                # Count passed/failed tests
                passed = sum([1 for k, v in test_data.items() if k.endswith('_test') and v == 'PASS'])
                failed = sum([1 for k, v in test_data.items() if k.endswith('_test') and v == 'FAIL'])
                
                messagebox.showinfo("Success", 
                    f"Test results saved successfully!\n\n"
                    f"Employee: {self.employee_name} ({self.employee_id})\n"
                    f"Camera: {camera_serial}\n"
                    f"Tests Passed: {passed}/4\n"
                    f"Tests Failed: {failed}/4\n"
                    f"Test ID: {test_id}")
                
                # Reset for next camera
                self.reset_test_session()
            else:
                messagebox.showerror("Error", "Failed to save test results")
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
            messagebox.showerror("Error", f"Failed to save results: {str(e)}")
    
    def open_results_viewer(self):
        """Open results viewer window"""
        import subprocess
        import sys
        from pathlib import Path
        
        # Get path to view_results.py
        project_root = Path(__file__).resolve().parent.parent.parent
        viewer_path = project_root / "opencv_tkinter" / "view_results.py"
        
        # Launch in separate process
        try:
            subprocess.Popen([sys.executable, str(viewer_path)])
            self.log_message("📊 Opened Results Viewer", 'status')
        except Exception as e:
            self.logger.error(f"Failed to open viewer: {e}")
            messagebox.showerror("Error", f"Failed to open viewer: {e}")