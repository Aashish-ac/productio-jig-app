import json
import os
from pathlib import Path

class Config:
    def __init__(self):
        """Initialize configuration manager"""
        self.config_file = Path.home() / ".camera_test_tool" / "config.json"
        self.config_file.parent.mkdir(exist_ok=True)
        self.settings = self.load()
    
    def load(self):
        """Load settings from file, with defaults"""
        defaults = {
            "rtsp_url": "rtsp://192.168.2.2/main",
            "serial_port": "/dev/tty.usbserial-0001",
            "baud_rate": "57600",
            "last_employee_id": "",
            "last_employee_name": "",
            "auto_connect": False,
            "log_level": "INFO",
            "theme": "dark"
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    saved_settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    return {**defaults, **saved_settings}
            except Exception as e:
                print(f"Error loading config: {e}")
                return defaults
        return defaults
    
    def save(self):
        """Save settings to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """Set a setting value"""
        self.settings[key] = value
        self.save()
    
    def get_log_dir(self):
        """Get directory for logs"""
        log_dir = Path.home() / ".camera_test_tool" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

