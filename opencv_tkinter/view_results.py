#!/usr/bin/env python3
"""
Database Viewer - View test results and statistics
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from utils.database import DatabaseManager
from datetime import datetime

class DatabaseViewer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("📊 Test Results Database Viewer")
        self.root.geometry("1000x600")
        
        self.db = DatabaseManager()
        
        # Colors
        self.colors = {
            'bg': '#1e1e1e',
            'card_bg': '#2d2d2d',
            'accent': '#007acc',
            'success': '#28a745',
            'text': '#ffffff',
            'text_secondary': '#b0b0b0'
        }
        
        self.root.configure(bg=self.colors['bg'])
        self.create_widgets()
        self.load_results()
        
    def create_widgets(self):
        """Create viewer widgets"""
        # Title
        title_frame = tk.Frame(self.root, bg=self.colors['bg'])
        title_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(title_frame, 
                text="📊 Camera Test Results Database",
                bg=self.colors['bg'],
                fg=self.colors['text'],
                font=('Helvetica Neue', 16, 'bold')).pack(side='left')
        
        # Control buttons
        btn_frame = tk.Frame(title_frame, bg=self.colors['bg'])
        btn_frame.pack(side='right')
        
        tk.Button(btn_frame, text="🔄 Refresh",
                 command=self.load_results,
                 bg=self.colors['accent'],
                 fg='white',
                 relief='flat',
                 padx=10).pack(side='left', padx=2)
        
        tk.Button(btn_frame, text="📊 Statistics",
                 command=self.show_statistics,
                 bg=self.colors['success'],
                 fg='white',
                 relief='flat',
                 padx=10).pack(side='left', padx=2)
        
        tk.Button(btn_frame, text="💾 Export CSV",
                 command=self.export_csv,
                 bg=self.colors['accent'],
                 fg='white',
                 relief='flat',
                 padx=10).pack(side='left', padx=2)
        
        # Search frame
        search_frame = tk.Frame(self.root, bg=self.colors['bg'])
        search_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(search_frame, text="Search Employee ID:",
                bg=self.colors['bg'],
                fg=self.colors['text']).pack(side='left', padx=5)
        
        self.search_var = tk.StringVar()
        tk.Entry(search_frame, textvariable=self.search_var,
                width=20).pack(side='left', padx=5)
        
        tk.Button(search_frame, text="🔍 Search",
                 command=self.search_employee,
                 bg=self.colors['accent'],
                 fg='white',
                 relief='flat',
                 padx=10).pack(side='left', padx=2)
        
        tk.Button(search_frame, text="❌ Clear",
                 command=self.load_results,
                 bg=self.colors['bg'],
                 fg='white',
                 relief='flat',
                 padx=10).pack(side='left', padx=2)
        
        # Results table
        table_frame = tk.Frame(self.root, bg=self.colors['card_bg'])
        table_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Scrollbars
        y_scroll = tk.Scrollbar(table_frame)
        y_scroll.pack(side='right', fill='y')
        
        x_scroll = tk.Scrollbar(table_frame, orient='horizontal')
        x_scroll.pack(side='bottom', fill='x')
        
        # Treeview
        columns = ('ID', 'Employee', 'Name', 'Camera', 'LED', 'IR_LED', 'IRCUT', 'Speaker', 'Date')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                yscrollcommand=y_scroll.set,
                                xscrollcommand=x_scroll.set)
        
        # Configure scrollbars
        y_scroll.config(command=self.tree.yview)
        x_scroll.config(command=self.tree.xview)
        
        # Column headings with better widths
        widths = {
            'ID': 50,
            'Employee': 100,
            'Name': 150,
            'Camera': 100,
            'LED': 80,
            'IR_LED': 80,
            'IRCUT': 80,
            'Speaker': 80,
            'Date': 150
        }
        
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by(c))
            self.tree.column(col, width=widths.get(col, 100))

        # Add striped rows for better readability
        self.tree.tag_configure('oddrow', background='#333333')
        self.tree.tag_configure('evenrow', background='#2d2d2d')
        
        self.tree.pack(fill='both', expand=True)
        
        # Configure tags for pass/fail colors
        self.tree.tag_configure('pass', foreground='#28a745')
        self.tree.tag_configure('fail', foreground='#dc3545')
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(self.root, textvariable=self.status_var,
                             bg=self.colors['card_bg'],
                             fg=self.colors['text_secondary'],
                             anchor='w')
        status_bar.pack(fill='x', padx=10, pady=5)
    
    def load_results(self):
        """Load all test results"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Load from database
        results = self.db.get_all_tests(limit=100)
        
        for i, row in enumerate(results):
            # Format date for better readability
            date_str = datetime.strptime(row[7], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M')
            
            values = (
                row[0],          # ID
                row[1],          # Employee ID
                row[9] if len(row) > 9 else 'Unknown',  # Name
                row[2],          # Camera serial
                row[3],          # LED
                row[4],          # IR LED
                row[5],          # IRCUT
                row[6],          # Speaker
                date_str         # Formatted date
            )
            
            # Add alternating row colors
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            
            # Color PASS/FAIL
            test_tags = [tag]
            if all(t == 'PASS' for t in row[3:7]):  # Check all test results
                test_tags.append('pass')
            elif any(t == 'FAIL' for t in row[3:7]):
                test_tags.append('fail')
                
            self.tree.insert('', 'end', values=values, tags=test_tags)
        
        self.status_var.set(f"Loaded {len(results)} test results")
    
    def search_employee(self):
        """Search results by employee ID"""
        employee_id = self.search_var.get().strip()
        
        if not employee_id:
            messagebox.showwarning("Warning", "Please enter Employee ID")
            return
        
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Load from database
        results = self.db.get_employee_tests(employee_id, limit=50)
        
        if not results:
            messagebox.showinfo("No Results", f"No tests found for Employee ID: {employee_id}")
            self.status_var.set(f"No results for {employee_id}")
            return
        
        for row in results:
            values = (
                row[0],  # ID
                row[1],  # Employee ID
                '',      # Name (not in employee_tests query)
                row[2],  # Camera serial
                row[3],  # LED
                row[4],  # IR LED
                row[5],  # IRCUT
                row[6],  # Speaker
                row[7]   # Date
            )
            self.tree.insert('', 'end', values=values)
        
        self.status_var.set(f"Found {len(results)} tests for {employee_id}")
    
    def show_statistics(self):
        """Show test statistics"""
        stats = self.db.get_test_statistics()
        
        stats_window = tk.Toplevel(self.root)
        stats_window.title("📊 Test Statistics")
        stats_window.geometry("400x400")
        stats_window.configure(bg=self.colors['bg'])
        
        # Title
        tk.Label(stats_window, text="📊 Test Statistics",
                bg=self.colors['bg'],
                fg=self.colors['text'],
                font=('Helvetica Neue', 14, 'bold')).pack(pady=10)
        
        # Stats frame
        stats_frame = tk.Frame(stats_window, bg=self.colors['card_bg'])
        stats_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Total tests
        tk.Label(stats_frame, text=f"Total Tests: {stats['total_tests']}",
                bg=self.colors['card_bg'],
                fg=self.colors['text'],
                font=('Helvetica Neue', 12, 'bold')).pack(pady=10)
        
        # Component statistics
        for component, data in stats.items():
            if component == 'total_tests':
                continue
            
            component_name = component.replace('_test', '').upper()
            passed = data['passed']
            failed = data['failed']
            total = passed + failed
            pass_rate = (passed / total * 100) if total > 0 else 0
            
            frame = tk.Frame(stats_frame, bg=self.colors['card_bg'])
            frame.pack(fill='x', pady=5, padx=10)
            
            tk.Label(frame, text=f"{component_name}:",
                    bg=self.colors['card_bg'],
                    fg=self.colors['text'],
                    font=('Helvetica Neue', 10, 'bold'),
                    width=10, anchor='w').pack(side='left')
            
            tk.Label(frame, text=f"✓ {passed}",
                    bg=self.colors['card_bg'],
                    fg='#28a745',
                    font=('Helvetica Neue', 10),
                    width=8).pack(side='left')
            
            tk.Label(frame, text=f"✗ {failed}",
                    bg=self.colors['card_bg'],
                    fg='#dc3545',
                    font=('Helvetica Neue', 10),
                    width=8).pack(side='left')
            
            tk.Label(frame, text=f"({pass_rate:.1f}%)",
                    bg=self.colors['card_bg'],
                    fg=self.colors['text_secondary'],
                    font=('Helvetica Neue', 10)).pack(side='left')
    
    def export_csv(self):
        """Export database to CSV"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"test_results_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        
        if file_path:
            try:
                self.db.export_to_csv(file_path)
                messagebox.showinfo("Success", f"Data exported to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export:\n{e}")
    
    def sort_by(self, column):
        """Sort treeview by column"""
        # This is a placeholder - implement sorting if needed
        pass
    
    def run(self):
        """Start the viewer"""
        self.root.mainloop()

if __name__ == "__main__":
    viewer = DatabaseViewer()
    viewer.run()