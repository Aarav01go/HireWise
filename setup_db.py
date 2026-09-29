import sqlite3

def setup_database():
    """
    Initializes the SQLite database for the HireWise HRMS application.
    Creates necessary tables (users, employees, leaves) and populates
    them with initial dummy data for testing purposes.
    """
    print("Connecting to the database...")
    # Connect to the local SQLite database file (creates it if it doesn't exist)
    conn = sqlite3.connect('hrms.db')
    cursor = conn.cursor()

    # Create the Users table for login credentials and role management
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        employee_id INTEGER
    )
    ''')

    # Create the Employees table to store profile details and leave balances
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        department TEXT,
        designation TEXT,
        join_date TEXT,
        salary REAL,
        leave_balance INTEGER DEFAULT 20
    )
    ''')

    # Create the Leaves table to track all time-off requests
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS leaves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        leave_type TEXT,
        start_date TEXT,
        end_date TEXT,
        reason TEXT,
        status TEXT DEFAULT 'Pending',
        applied_on TEXT,
        FOREIGN KEY (employee_id) REFERENCES employees (id)
    )
    ''')

    print("Clearing out any old data to start fresh...")
    # Clean up old data if the script is run multiple times
    cursor.execute('DELETE FROM leaves')
    cursor.execute('DELETE FROM users')
    cursor.execute('DELETE FROM employees')
    
    # Reset the auto-increment counters so IDs start at 1 again
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('leaves', 'users', 'employees')")

    print("Inserting dummy employee records...")
    # A list of initial employees to populate our HR directory
    dummy_employees = [
        ('Alice HR', 'alice@hirewise.com', 'HR', 'HR Manager', '2020-01-15', 85000, 20),
        ('Bob Engineer', 'bob@hirewise.com', 'Engineering', 'Software Engineer', '2021-03-10', 95000, 15),
        ('Charlie Sales', 'charlie@hirewise.com', 'Sales', 'Sales Exec', '2022-06-01', 65000, 10),
        ('Diana Market', 'diana@hirewise.com', 'Marketing', 'Marketing Lead', '2019-11-20', 90000, 25),
        ('Aarav Gupta', 'aarav@hirewise.com', 'Engineering', 'Junior Dev', '2023-08-01', 60000, 12)
    ]
    cursor.executemany('''
    INSERT INTO employees (name, email, department, designation, join_date, salary, leave_balance)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', dummy_employees)
    
    # Retrieve the dynamically generated IDs for Alice (HR) and Aarav (Employee)
    # This ensures we link their user accounts to the correct employee profile
    cursor.execute("SELECT id FROM employees WHERE name='Alice HR'")
    alice_id = cursor.fetchone()[0]
    
    cursor.execute("SELECT id FROM employees WHERE name='Aarav Gupta'")
    aarav_id = cursor.fetchone()[0]

    print("Setting up user login accounts...")
    # Create the actual login credentials
    # Note: Passwords are in plain text here for simplicity in this demo project.
    dummy_users = [
        ('hr', 'hr123', 'HR', alice_id),
        ('aarav', 'emp123', 'Employee', aarav_id)
    ]
    cursor.executemany('''
    INSERT INTO users (username, password_hash, role, employee_id)
    VALUES (?, ?, ?, ?)
    ''', dummy_users)

    # Save all changes and close the connection
    conn.commit()
    conn.close()
    print("Success: 'hrms.db' database created and populated with dummy data!")

if __name__ == '__main__':
    setup_database()
