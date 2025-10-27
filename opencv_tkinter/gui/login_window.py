import tkinter as tk
from tkinter import ttk, messagebox
import platform
from ..utils.database import DatabaseManager
from .styles import GUIStyles

class LoginWindow:
    def __init__(self, on_login_success):
        """
        Employee login window
        Args:
            on_login_success: Callback function(employee_id, employee_name)
        """
        self.on_login_success = on_login_success
        self.db = DatabaseManager()
        self.employee_id = None
        self.employee_name = None
        
        # Initialize styles
        self.styles = GUIStyles()
        
        # Create window
        self.root = tk.Tk()
        self.root.title("Employee Login")
        self.root.geometry("400x450")
        self.root.resizable(False, False)
        
        # Apply theme
        self.styles.setup_styles()
        self.root.configure(bg=self.styles.colors['bg'])
        
        self.create_widgets()
        self.center_window()
        self.employee_id_entry.focus()
        
    def center_window(self):
        """Center window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        """Create login form widgets using pure ttk for cross-platform compatibility"""
        # Main container using ttk Frame with Card style
        main_frame = ttk.Frame(self.root, style='Card.TFrame', padding=30)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        ttk.Label(main_frame, 
                 text="Camera Test Station",
                 style='Title.TLabel').pack(pady=(30, 10))
        
        ttk.Label(main_frame,
                 text="Production Line Login",
                 style='Hint.TLabel').pack(pady=(0, 30))
        
        # Employee ID section
        ttk.Label(main_frame, 
                 text="Employee ID:",
                 style='Body.TLabel').pack(anchor='w', pady=(10, 4))
        
        self.employee_id_var = tk.StringVar()
        self.employee_id_entry = ttk.Entry(main_frame,
                                          textvariable=self.employee_id_var,
                                          style='Form.TEntry')
        self.employee_id_entry.pack(fill='x', pady=(0, 12))
        self.employee_id_entry.bind('<Return>', lambda e: self.check_employee())
        
        # Employee Name section
        ttk.Label(main_frame,
                 text="Employee Name:",
                 style='Body.TLabel').pack(anchor='w', pady=(10, 4))
        
        self.employee_name_var = tk.StringVar()
        self.employee_name_entry = ttk.Entry(main_frame,
                                            textvariable=self.employee_name_var,
                                            style='Form.TEntry')
        self.employee_name_entry.pack(fill='x', pady=(0, 12))
        self.employee_name_entry.bind('<Return>', lambda e: self.login())
        
        # Login button using ttk with Success style
        self.login_btn = ttk.Button(main_frame,
                                   text="Login",
                                   command=self.login,
                                   style='Success.TButton')
        self.login_btn.pack(fill='x', pady=(20, 0))
        
        # Status label
        self.status_var = tk.StringVar(value="Please enter your credentials")
        self.status_label = ttk.Label(main_frame,
                                     textvariable=self.status_var,
                                     style='Status.TLabel')
        self.status_label.pack(pady=(15, 0))
        
        # Hint
        ttk.Label(main_frame,
                 text="Press Enter to move between fields",
                 style='Hint.TLabel').pack(side='bottom', pady=(0, 20))
    
    def check_employee(self):
        """Check if employee exists and auto-fill name"""
        employee_id = self.employee_id_var.get().strip()
        
        if not employee_id:
            return
        
        employee = self.db.get_employee(employee_id)
        
        if employee:
            self.employee_name_var.set(employee[1])
            self.status_var.set(f"Welcome back, {employee[1]}!")
            self.status_label.configure(style='Success.TLabel')
            self.login_btn.focus()
        else:
            self.employee_name_entry.focus()
            self.status_var.set("New employee - please enter your name")
            self.status_label.configure(style='Status.TLabel')
    
    def login(self):
        """Process login"""
        employee_id = self.employee_id_var.get().strip()
        employee_name = self.employee_name_var.get().strip()
        
        if not employee_id:
            messagebox.showerror("Error", "Please enter Employee ID")
            self.employee_id_entry.focus()
            return
        
        if not employee_name:
            messagebox.showerror("Error", "Please enter Employee Name")
            self.employee_name_entry.focus()
            return
        
        success = self.db.add_employee(employee_id, employee_name)
        
        if success:
            self.employee_id = employee_id
            self.employee_name = employee_name
            self.status_var.set("Login successful!")
            self.status_label.configure(style='Success.TLabel')
            self.root.after(500, self.complete_login)
        else:
            messagebox.showerror("Error", "Failed to login. Please try again.")
    
    def complete_login(self):
        """Complete login and open main app"""
        self.root.destroy()
        if self.on_login_success:
            self.on_login_success(self.employee_id, self.employee_name)
    
    def run(self):
        """Start login window"""
        self.root.mainloop()
        return self.employee_id, self.employee_name