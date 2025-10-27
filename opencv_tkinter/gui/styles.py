from tkinter import ttk
import platform
import subprocess
import sys

class GUIStyles:
    def __init__(self):
        # Detect macOS appearance mode
        self.is_dark_mode = self._detect_dark_mode()
        
        if self.is_dark_mode:
            self.colors = {
                'bg': '#1e1e1e',           # Dark background
                'card_bg': '#2d2d2d',      # Card background
                'accent': '#007acc',        # Blue accent
                'success': '#28a745',       # Green for success
                'warning': '#ffc107',       # Yellow for warning
                'danger': '#dc3545',        # Red for danger
                'text': '#ffffff',          # White text
                'text_secondary': '#b0b0b0' # Gray text
            }
        else:
            # Light mode colors
            self.colors = {
                'bg': '#f8f9fa',           # Light background
                'card_bg': '#ffffff',       # White card background
                'accent': '#007acc',        # Blue accent
                'success': '#28a745',       # Green for success
                'warning': '#ffc107',       # Yellow for warning
                'danger': '#dc3545',        # Red for danger
                'text': '#212529',          # Dark text
                'text_secondary': '#6c757d'  # Gray text
            }
    
    def _detect_dark_mode(self):
        """Detect if macOS is in dark mode"""
        if platform.system() != 'Darwin':
            return False
        
        try:
            # Use osascript to detect dark mode
            result = subprocess.run([
                'osascript', '-e', 
                'tell application "System Events" to tell appearance preferences to get dark mode'
            ], capture_output=True, text=True, timeout=5)
            return 'true' in result.stdout.lower()
        except:
            # Fallback to light mode if detection fails (safer default)
            return False

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Set default colors for all ttk widgets
        style.configure('.', 
                       background=self.colors['bg'], 
                       foreground=self.colors['text'])
        
        # Title label style
        style.configure('Title.TLabel', 
                       background=self.colors['card_bg'],
                       foreground=self.colors['text'],
                       font=('Helvetica Neue', 16, 'bold'))
        
        # Body label style
        style.configure('Body.TLabel',
                       background=self.colors['card_bg'],
                       foreground=self.colors['text'],
                       font=('Helvetica Neue', 10))
        
        # Hint label style
        style.configure('Hint.TLabel',
                       background=self.colors['card_bg'],
                       foreground=self.colors['text_secondary'],
                       font=('Helvetica Neue', 9))
        
        # Status label style
        style.configure('Status.TLabel',
                       background=self.colors['card_bg'],
                       foreground=self.colors['text_secondary'],
                       font=('Helvetica Neue', 9))
        
        # Success label style
        style.configure('Success.TLabel',
                       background=self.colors['card_bg'],
                       foreground=self.colors['success'],
                       font=('Helvetica Neue', 9))
        
        # Card frame style
        style.configure('Card.TFrame',
                       background=self.colors['card_bg'],
                       relief='raised',
                       borderwidth=2)
        
        # Form Entry style
        style.configure('Form.TEntry',
                       fieldbackground=self.colors['card_bg'],
                       foreground=self.colors['text'],
                       font=('Helvetica Neue', 10),
                       padding=(8, 6))
        
        # Ensure Entry borders are visible
        style.map('Form.TEntry',
                 fieldbackground=[('focus', self.colors['card_bg']),
                                 ('!focus', self.colors['card_bg'])],
                 bordercolor=[('focus', self.colors['accent']),
                            ('!focus', '#cccccc')])
        
        # Ensure background paints on macOS/Aqua
        style.layout('Pill.TButton', [
            ('Button.focus', {'children': [
                ('Button.border', {'border': 1, 'children': [
                    ('Button.padding', {'children': [
                        ('Button.label', {'sticky': 'nswe'})
                    ], 'sticky': 'nswe'})
                ], 'sticky': 'nswe'})
            ], 'sticky': 'nswe'})
        ])
        
        style.configure('Pill.TButton',
                        background=self.colors['accent'],
                        foreground='white',
                        bordercolor=self.colors['accent'],
                        padding=(10, 8),
                        relief='flat')
        style.map('Pill.TButton',
                  background=[('pressed', '#0c6fd1'), ('active', '#1491ff'), ('!disabled', self.colors['accent'])],
                  foreground=[('disabled', '#c0c0c0'), ('!disabled', 'white')])
        
        style.configure('Success.TButton',
                        background=self.colors['success'],
                        foreground='white',
                        bordercolor=self.colors['success'],
                        padding=(10, 8),
                        relief='flat')
        style.map('Success.TButton',
                  background=[('pressed', '#1d7a33'), ('active', '#23923d'), ('!disabled', self.colors['success'])],
                  foreground=[('disabled', '#c0c0c0'), ('!disabled', 'white')])
        
        style.configure('Modern.TButton',
                        background=self.colors['accent'],
                        foreground='white',
                        bordercolor=self.colors['accent'],
                        padding=(10, 8),
                        relief='flat')
        style.map('Modern.TButton',
                  background=[('pressed', '#0c6fd1'), ('active', '#1491ff'), ('!disabled', self.colors['accent'])],
                  foreground=[('disabled', '#c0c0c0'), ('!disabled', 'white')])
        
        style.configure('Danger.TButton',
                        background=self.colors['danger'],
                        foreground='white',
                        bordercolor=self.colors['danger'],
                        padding=(10, 8),
                        relief='flat')
        style.map('Danger.TButton',
                  background=[('pressed', '#bd2130'), ('active', '#c82333'), ('!disabled', self.colors['danger'])],
                  foreground=[('disabled', '#c0c0c0'), ('!disabled', 'white')])
