#!/usr/bin/env python3
"""
Creative Camera Test GUI Application
Professional Production Testing Tool with Modern UI and Video Stream
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import traceback
from pathlib import Path
from datetime import datetime

# Suppress Tk deprecation warning on macOS
os.environ['TK_SILENCE_DEPRECATION'] = '1'

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from opencv_tkinter.gui.main_window import CameraTestGUI
from opencv_tkinter.gui.login_window import LoginWindow


def exception_handler(exc_type, exc_value, exc_traceback):
    """Global exception handler for crash recovery"""
    error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    # Log to file
    log_file = Path.home() / ".camera_test_tool" / "crash.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_file, 'a') as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"Crash at {datetime.now()}\n")
        f.write(error_msg)
    
    # Show user-friendly error
    try:
        messagebox.showerror(
            "Application Error",
            "An unexpected error occurred. Details have been logged.\n\n"
            f"Please check: {log_file}"
        )
    except:
        print(f"Application crashed. Log saved to: {log_file}")
    
    sys.exit(1)


def main():
    """Main entry point"""
    # Set global exception handler
    sys.excepthook = exception_handler
    
    def on_login_success(employee_id, employee_name):
        """Callback when login is successful"""
        # Create main application window with single Tk instance
        root = tk.Tk()
        app = CameraTestGUI(root, employee_id=employee_id, employee_name=employee_name)
        
        # Handle window close
        def on_closing():
            try:
                app.on_closing()
            except:
                pass
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Start main event loop
        root.mainloop()
    
    # Step 1: Create and run login window (blocks until login completes)
    login = LoginWindow(on_login_success)
    login.run()


if __name__ == "__main__":
    main()