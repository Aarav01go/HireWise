import sqlite3
import datetime

def setup_database():
    # Connect to SQLite (this automatically creates the file hrms.db if it doesn't exist)
    conn = sqlite3.connect('hrms.db')
    cursor = conn.cursor()

    # 1. Create Employees table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        department TEXT NOT NULL,
        designation TEXT NOT NULL,
        join_date TEXT NOT NULL,
        salary REAL NOT NULL,
        leave_balance INTEGER NOT NULL
    )
    ''')

    # 2. Create Users table (Stores logins)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        employee_id INTEGER,
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    ''')

    # 3. Create Leaves table (Tracks leave requests)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS leaves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        leave_type TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        reason TEXT,
        status TEXT NOT NULL,
        applied_on TEXT NOT NULL,
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    ''')

    # Clear existing data so we don't duplicate rows if you run this twice
    cursor.execute('DELETE FROM leaves')
    cursor.execute('DELETE FROM users')
    cursor.execute('DELETE FROM employees')

    # --- INSERT DUMMY DATA ---
    
    # 5 Dummy Employees
    employees_data = [
        ('Alice HR', 'alice@hirewise.com', 'HR', 'HR Manager', '2020-01-15', 85000, 20),
        ('Bob Engineer', 'bob@hirewise.com', 'Engineering', 'Software Engineer', '2021-03-10', 95000, 15),
        ('Charlie Sales', 'charlie@hirewise.com', 'Sales', 'Sales Exec', '2022-06-01', 65000, 10),
        ('Diana Market', 'diana@hirewise.com', 'Marketing', 'Marketing Lead', '2019-11-20', 90000, 25),
        ('Aarav Patel', 'aarav@hirewise.com', 'Engineering', 'Junior Dev', '2023-08-01', 60000, 12)
    ]
    cursor.executemany('''
    INSERT INTO employees (name, email, department, designation, join_date, salary, leave_balance)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', employees_data)

    # Get the auto-generated IDs for Alice and Aarav to link to their user accounts
    cursor.execute("SELECT id FROM employees WHERE name='Alice HR'")
    alice_id = cursor.fetchone()[0]
    
    cursor.execute("SELECT id FROM employees WHERE name='Aarav Patel'")
    aarav_id = cursor.fetchone()[0]

    # Create 2 Dummy Logins (1 HR, 1 Employee)
    # Note: We are using plain text passwords like 'hr123' for simplicity right now.
    users_data = [
        ('hr', 'hr123', 'HR', alice_id),
        ('aarav', 'emp123', 'Employee', aarav_id)
    ]
    cursor.executemany('''
    INSERT INTO users (username, password_hash, role, employee_id)
    VALUES (?, ?, ?, ?)
    ''', users_data)

    # Create 2 Dummy Leave Requests
    today = datetime.date.today().strftime('%Y-%m-%d')
    leaves_data = [
        (aarav_id, 'Sick Leave', '2023-10-01', '2023-10-02', 'Fever', 'Approved', today),
        (aarav_id, 'Casual Leave', '2023-11-15', '2023-11-20', 'Family trip', 'Pending', today)
    ]
    cursor.executemany('''
    INSERT INTO leaves (employee_id, leave_type, start_date, end_date, reason, status, applied_on)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', leaves_data)

    # Save changes and close
    conn.commit()
    conn.close()
    print("Success: 'hrms.db' database created and populated with dummy data!")

if __name__ == "__main__":
    setup_database()
