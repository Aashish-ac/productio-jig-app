import tkinter as tk
from tkinter import ttk, scrolledtext

class LogWindow:
    def __init__(self, parent_app):
        self.parent_app = parent_app
        self.window = None
        self.logs_text = None
        # Store reference to main window's logs_text
        self.main_logs_text = parent_app.logs_text
        
    def show_window(self):
        """Show the terminal window"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return
            
        self.window = tk.Toplevel(self.parent_app.root)
        self.window.title("📋 Terminal Log")
        self.window.geometry("800x600")
        self.window.configure(bg=self.parent_app.colors['bg'])
        
        self.create_logs_panel()
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Add reference to main app so it can write to this window
        self.parent_app.log_window_ref = self
        
        # Copy existing logs from main window
        if self.main_logs_text:
            existing_logs = self.main_logs_text.get(1.0, tk.END)
            self.logs_text.insert(tk.END, existing_logs)
        
        # Force an initial test message to verify logging
        self.parent_app.log_message("Terminal window opened", 'status')

    def create_logs_panel(self):
        """Create terminal display panel"""
        frame = ttk.Frame(self.window, style='Card.TFrame', padding=10)
        frame.pack(fill='both', expand=True)
        
        # Header with controls
        header = tk.Frame(frame, bg=self.parent_app.colors['card_bg'])
        header.pack(fill='x', pady=(0, 5))
        
        tk.Label(header, text="📋 Terminal Log",
                bg=self.parent_app.colors['card_bg'],
                fg=self.parent_app.colors['text'],
                font=('Helvetica Neue', 12, 'bold')).pack(side='left')
        
        # Control buttons
        ttk.Button(header, text="🗑️ Clear", 
                  command=self.clear_logs,
                  style='Modern.TButton').pack(side='right', padx=5)
                  
        ttk.Button(header, text="💾 Save", 
                  command=self.save_logs,
                  style='Modern.TButton').pack(side='right')
        
        # Auto-scroll option
        tk.Checkbutton(header, text="Auto-scroll",
                      variable=self.parent_app.autoscroll_var,
                      bg=self.parent_app.colors['card_bg'],
                      fg=self.parent_app.colors['text']).pack(side='right', padx=10)
        
        # Terminal output area - OWN widget, not overwriting parent's
        self.logs_text = scrolledtext.ScrolledText(
            frame, height=15,
            bg=self.parent_app.colors['bg'],
            fg=self.parent_app.colors['text'],
            insertbackground=self.parent_app.colors['text'],
            font=('Consolas', 10))
        self.logs_text.pack(fill='both', expand=True, pady=5)
        
        # Configure text tags
        self.logs_text.tag_configure('sent', foreground='#87CEEB')
        self.logs_text.tag_configure('received', foreground='#98FB98')
        self.logs_text.tag_configure('status', foreground='#FFD700')
        self.logs_text.tag_configure('error', foreground='#FF6B6B')
        self.logs_text.tag_configure('ready', foreground='#FF69B4', font=('Consolas', 10, 'bold'))
    
    def clear_logs(self):
        """Clear the logs text area"""
        if self.logs_text:
            self.logs_text.delete(1.0, tk.END)
    
    def save_logs(self):
        """Save logs to a file"""
        if not self.logs_text:
            return
            
        logs = self.logs_text.get(1.0, tk.END).strip()
        if not logs:
            tk.messagebox.showinfo("Info", "No logs to save")
            return
        
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Logs As")
        
        if not file_path:
            return
        
        try:
            with open(file_path, "w") as file:
                file.write(logs)
            tk.messagebox.showinfo("Success", "Logs saved successfully")
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to save logs: {str(e)}")

    def on_closing(self):
        """Handle window closing"""
        # Remove reference from parent app
        if hasattr(self.parent_app, 'log_window_ref'):
            self.parent_app.log_window_ref = None
        if self.window:
            self.window.destroy()
            self.window = None
