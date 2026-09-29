import sqlite3
import pandas as pd
from datetime import date, timedelta

def setup_database():
    print("Connecting to database...")
    conn = sqlite3.connect('hrms.db')
    cursor = conn.cursor()

    print("Creating tables...")
    # Create employees table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            department TEXT,
            designation TEXT,
            join_date DATE,
            salary REAL,
            leave_balance INTEGER DEFAULT 20
        )
    ''')

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            employee_id INTEGER,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')

    # Create leaves table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leaves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            leave_type TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'Pending',
            applied_on DATE NOT NULL,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')

    # Check if we already have data
    cursor.execute('SELECT COUNT(*) FROM employees')
    if cursor.fetchone()[0] == 0:
        print("Inserting dummy data...")
        
        # Insert Employees
        employees_data = [
            ('Alice Smith', 'alice@example.com', 'HR', 'HR Manager', '2022-01-15', 80000, 20),
            ('Bob Jones', 'bob@example.com', 'Engineering', 'Software Engineer', '2023-03-01', 90000, 15),
            ('Charlie Brown', 'charlie@example.com', 'Engineering', 'DevOps Engineer', '2022-11-10', 95000, 18),
            ('Diana Prince', 'diana@example.com', 'Marketing', 'Marketing Specialist', '2024-02-20', 70000, 20),
            ('Evan Davis', 'evan@example.com', 'Sales', 'Sales Representative', '2023-08-05', 75000, 12)
        ]
        cursor.executemany('''
            INSERT INTO employees (name, email, department, designation, join_date, salary, leave_balance)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', employees_data)
        
        # Insert Users (passwords are stored as plain text for dummy purposes initially, normally hashed)
        users_data = [
            ('hr_alice', 'password123', 'HR', 1),
            ('emp_bob', 'password123', 'Employee', 2),
            ('emp_charlie', 'password123', 'Employee', 3)
        ]
        cursor.executemany('''
            INSERT INTO users (username, password_hash, role, employee_id)
            VALUES (?, ?, ?, ?)
        ''', users_data)
        
        # Insert Leaves
        today = date.today()
        leaves_data = [
            (2, 'Sick Leave', today.strftime('%Y-%m-%d'), (today + timedelta(days=1)).strftime('%Y-%m-%d'), 'Fever', 'Approved', (today - timedelta(days=2)).strftime('%Y-%m-%d')),
            (3, 'Annual Leave', (today + timedelta(days=10)).strftime('%Y-%m-%d'), (today + timedelta(days=15)).strftime('%Y-%m-%d'), 'Vacation', 'Pending', today.strftime('%Y-%m-%d'))
        ]
        cursor.executemany('''
            INSERT INTO leaves (employee_id, leave_type, start_date, end_date, reason, status, applied_on)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', leaves_data)
        
    conn.commit()
    conn.close()
    print("Database setup complete!")

if __name__ == '__main__':
    setup_database()
