import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="HireWise HRMS", page_icon="🏢", layout="wide")

def get_db_connection():
    conn = sqlite3.connect('hrms.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Note: Plain text password comparison for dummy data
    cursor.execute("SELECT * FROM users WHERE username=? AND password_hash=?", (username, password))
    user = cursor.fetchone()
    conn.close()
    return user

def display_login():
    st.title("🏢 Welcome to HireWise")
    st.subheader("Please Login")
    
    with st.form("login_form"):
        username = st.text_input("Username", autocomplete="new-password")
        password = st.text_input("Password", type="password", autocomplete="new-password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            user = login_user(username, password)
            if user:
                st.session_state['logged_in'] = True
                st.session_state['username'] = user['username']
                st.session_state['role'] = user['role']
                st.session_state['employee_id'] = user['employee_id']
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid Username or Password")

def display_hr_dashboard():
    st.title("👥 HR Dashboard - Employee Management")
    
    tab1, tab2 = st.tabs(["View Employees", "Add New Employee"])
    
    with tab1:
        st.subheader("Employee Records")
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT id, name, email, department, designation, join_date, salary, leave_balance FROM employees", conn)
        conn.close()
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    with tab2:
        st.subheader("Add Employee")
        with st.form("add_employee_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            department = st.selectbox("Department", ["HR", "Engineering", "Sales", "Marketing", "Finance"])
            designation = st.text_input("Designation")
            join_date = st.date_input("Join Date")
            salary = st.number_input("Salary", min_value=0, step=1000)
            leave_balance = st.number_input("Starting Leave Balance", min_value=0, value=20)
            
            submitted = st.form_submit_button("Add Employee")
            if submitted:
                if name and email and designation:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute('''
                        INSERT INTO employees (name, email, department, designation, join_date, salary, leave_balance)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (name, email, department, designation, join_date.strftime('%Y-%m-%d'), salary, leave_balance))
                        conn.commit()
                        st.success(f"Employee {name} added successfully!")
                    except sqlite3.IntegrityError:
                        st.error("An employee with this email already exists.")
                    finally:
                        conn.close()
                else:
                    st.error("Please fill in all required fields.")

def display_employee_dashboard():
    st.title("👋 Employee Portal")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE id=?", (st.session_state['employee_id'],))
    emp = cursor.fetchone()
    conn.close()
    
    if emp:
        st.subheader(f"Welcome, {emp['name']}")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Email:** {emp['email']}")
            st.write(f"**Department:** {emp['department']}")
            st.write(f"**Designation:** {emp['designation']}")
        with col2:
            st.write(f"**Join Date:** {emp['join_date']}")
            st.write(f"**Leave Balance:** {emp['leave_balance']} days")
            
        st.info("Your Leave Management features will appear here on Day 3!")

def main():
    # Initialize session state for login
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    # Sidebar for logout
    if st.session_state['logged_in']:
        with st.sidebar:
            st.write(f"Logged in as: **{st.session_state['username']}** ({st.session_state['role']})")
            if st.button("Logout"):
                st.session_state.clear()
                st.rerun()

    # Route to correct page
    if not st.session_state['logged_in']:
        display_login()
    else:
        if st.session_state['role'] == 'HR':
            display_hr_dashboard()
        else:
            display_employee_dashboard()

if __name__ == '__main__':
    main()
