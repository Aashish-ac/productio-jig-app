import sqlite3
from datetime import datetime
import os

class DatabaseManager:
    def __init__(self, db_path="camera_tests.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self.create_tables()
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def create_tables(self):
        """Create necessary tables if they don't exist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Employees table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                employee_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Test results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                camera_serial TEXT,
                led_test TEXT NOT NULL,
                irled_test TEXT NOT NULL,
                ircut_test TEXT NOT NULL,
                speaker_test TEXT NOT NULL,
                test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees (employee_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✓ Database initialized: {self.db_path}")
    
    def add_employee(self, employee_id, name):
        """Add or update employee"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO employees (employee_id, name)
                VALUES (?, ?)
            ''', (employee_id, name))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding employee: {e}")
            return False
        finally:
            conn.close()
    
    def get_employee(self, employee_id):
        """Get employee by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM employees WHERE employee_id = ?', (employee_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result
    
    def save_test_result(self, employee_id, test_data):
        """
        Save test result to database
        
        test_data = {
            'camera_serial': 'CAM12345',
            'led_test': 'PASS',
            'irled_test': 'PASS',
            'ircut_test': 'PASS',
            'speaker_test': 'PASS',
            'notes': 'Optional notes'
        }
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO test_results 
                (employee_id, camera_serial, led_test, irled_test, 
                 ircut_test, speaker_test, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                employee_id,
                test_data.get('camera_serial', 'UNKNOWN'),
                test_data.get('led_test', 'NOT_TESTED'),
                test_data.get('irled_test', 'NOT_TESTED'),
                test_data.get('ircut_test', 'NOT_TESTED'),
                test_data.get('speaker_test', 'NOT_TESTED'),
                test_data.get('notes', '')
            ))
            conn.commit()
            test_id = cursor.lastrowid
            print(f"✓ Test result saved with ID: {test_id}")
            return test_id
        except Exception as e:
            print(f"Error saving test result: {e}")
            return None
        finally:
            conn.close()
    
    def get_employee_tests(self, employee_id, limit=10):
        """Get recent tests by employee"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM test_results 
            WHERE employee_id = ? 
            ORDER BY test_date DESC 
            LIMIT ?
        ''', (employee_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_all_tests(self, limit=50):
        """Get all recent tests"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT t.*, e.name 
            FROM test_results t
            LEFT JOIN employees e ON t.employee_id = e.employee_id
            ORDER BY t.test_date DESC 
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_test_statistics(self):
        """Get overall test statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total tests
        cursor.execute('SELECT COUNT(*) FROM test_results')
        stats['total_tests'] = cursor.fetchone()[0]
        
        # Tests by component
        for component in ['led_test', 'irled_test', 'ircut_test', 'speaker_test']:
            cursor.execute(f'''
                SELECT 
                    SUM(CASE WHEN {component} = 'PASS' THEN 1 ELSE 0 END) as passed,
                    SUM(CASE WHEN {component} = 'FAIL' THEN 1 ELSE 0 END) as failed
                FROM test_results
            ''')
            result = cursor.fetchone()
            stats[component] = {'passed': result[0] or 0, 'failed': result[1] or 0}
        
        conn.close()
        return stats
    
    def export_to_csv(self, filepath):
        """Export all test results to CSV"""
        import csv
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT t.*, e.name 
            FROM test_results t
            LEFT JOIN employees e ON t.employee_id = e.employee_id
            ORDER BY t.test_date DESC
        ''')
        
        results = cursor.fetchall()
        
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['ID', 'Employee_ID', 'Employee_Name', 'Camera_Serial', 
                           'LED', 'IR_LED', 'IRCUT', 'Speaker', 'Date', 'Notes'])
            
            for row in results:
                writer.writerow(row)
        
        conn.close()
        print(f"✓ Data exported to: {filepath}")
        return True