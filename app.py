import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import os
from dotenv import load_dotenv
from google import genai

# Load environment variables (for Gemini API Key)
load_dotenv()

try:
    gemini_client = genai.Client()
except Exception:
    gemini_client = None

st.set_page_config(page_title="HireWise HRMS", page_icon="🏢", layout="wide")

def get_db_connection():
    conn = sqlite3.connect('hrms.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
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
    
    tab1, tab2, tab3 = st.tabs(["View Employees", "Add New Employee", "Leave Requests"])
    
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
                    
    with tab3:
        st.subheader("Pending Leave Requests")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT l.id, e.name, l.leave_type, l.start_date, l.end_date, l.reason, l.applied_on
            FROM leaves l
            JOIN employees e ON l.employee_id = e.id
            WHERE l.status = 'Pending'
        ''')
        pending_leaves = cursor.fetchall()
        
        if not pending_leaves:
            st.info("No pending leave requests right now! 🎉")
        else:
            for leave in pending_leaves:
                with st.expander(f"{leave['name']} - {leave['leave_type']} ({leave['start_date']} to {leave['end_date']})"):
                    st.write(f"**Applied on:** {leave['applied_on']}")
                    st.write(f"**Reason:** {leave['reason']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Approve", key=f"approve_{leave['id']}"):
                            start = datetime.strptime(leave['start_date'], '%Y-%m-%d')
                            end = datetime.strptime(leave['end_date'], '%Y-%m-%d')
                            days_taken = (end - start).days + 1
                            
                            cursor.execute("UPDATE leaves SET status='Approved' WHERE id=?", (leave['id'],))
                            cursor.execute("UPDATE employees SET leave_balance = leave_balance - ? WHERE name=?", (days_taken, leave['name']))
                            conn.commit()
                            st.success("Leave Approved!")
                            st.rerun()
                            
                    with col2:
                        if st.button("❌ Reject", key=f"reject_{leave['id']}"):
                            cursor.execute("UPDATE leaves SET status='Rejected' WHERE id=?", (leave['id'],))
                            conn.commit()
                            st.error("Leave Rejected.")
                            st.rerun()
                            
        st.subheader("All Leave History")
        df_leaves = pd.read_sql_query('''
            SELECT l.id, e.name, l.leave_type, l.start_date, l.end_date, l.status
            FROM leaves l JOIN employees e ON l.employee_id = e.id
        ''', conn)
        st.dataframe(df_leaves, use_container_width=True, hide_index=True)
        conn.close()

def display_employee_dashboard():
    st.title("👋 Employee Portal")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE id=?", (st.session_state['employee_id'],))
    emp = cursor.fetchone()
    
    if emp:
        st.subheader(f"Welcome, {emp['name']}")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Email:** {emp['email']}")
            st.write(f"**Department:** {emp['department']}")
            st.write(f"**Designation:** {emp['designation']}")
        with col2:
            st.write(f"**Join Date:** {emp['join_date']}")
            st.metric(label="Leave Balance", value=f"{emp['leave_balance']} days")
            
        st.divider()
        
        tab1, tab2, tab3 = st.tabs(["Apply for Leave", "My Leave History", "🤖 HR Assistant Chatbot"])
        
        with tab1:
            st.subheader("📅 Apply for Time Off")
            with st.form("apply_leave_form"):
                leave_type = st.selectbox("Leave Type", ["Casual Leave", "Sick Leave", "Paid Leave", "Unpaid Leave"])
                
                c1, c2 = st.columns(2)
                with c1:
                    start_date = st.date_input("Start Date")
                with c2:
                    end_date = st.date_input("End Date")
                    
                reason = st.text_area("Reason for Leave")
                
                submitted = st.form_submit_button("Submit Application")
                if submitted:
                    if end_date < start_date:
                        st.error("End date cannot be before start date.")
                    else:
                        days_requested = (end_date - start_date).days + 1
                        if emp['leave_balance'] >= days_requested or leave_type == "Unpaid Leave":
                            cursor.execute('''
                            INSERT INTO leaves (employee_id, leave_type, start_date, end_date, reason, status, applied_on)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', (emp['id'], leave_type, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), reason, 'Pending', date.today().strftime('%Y-%m-%d')))
                            conn.commit()
                            st.success(f"Leave application for {days_requested} days submitted successfully!")
                            st.rerun() 
                        else:
                            st.error(f"Insufficient leave balance. You requested {days_requested} days, but only have {emp['leave_balance']} days available.")
                            
        with tab2:
            st.subheader("📖 Leave History")
            df = pd.read_sql_query("SELECT leave_type, start_date, end_date, reason, status, applied_on FROM leaves WHERE employee_id=?", conn, params=(emp['id'],))
            if df.empty:
                st.write("You haven't applied for any leaves yet.")
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
                
        with tab3:
            st.subheader("🤖 AI HR Assistant")
            st.info("I am an AI assistant integrated with Gemini. Ask me about company policy or your personal leave balance!")
            
            if 'chat_history' not in st.session_state:
                st.session_state['chat_history'] = []
                
            # Render chat history
            for msg in st.session_state['chat_history']:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    
            # Chat input
            user_question = st.chat_input("E.g. What is the notice period? or How many leaves do I have?")
            if user_question:
                # Add user question
                st.session_state['chat_history'].append({"role": "user", "content": user_question})
                with st.chat_message("user"):
                    st.markdown(user_question)
                    
                with st.chat_message("assistant"):
                    if not gemini_client:
                        st.error("Gemini API Client is not initialized. Please check your .env file and API key.")
                    else:
                        with st.spinner("Looking up HR Policies..."):
                            try:
                                # Read Policy Text
                                policy_text = ""
                                try:
                                    with open("docs/hr_policy.txt", "r") as f:
                                        policy_text = f.read()
                                except FileNotFoundError:
                                    policy_text = "No HR policy document found."
                                
                                # Construct the Prompt with Context (RAG)
                                prompt = f"""
                                You are HireWise, a helpful and professional HR Assistant Chatbot.
                                You are talking directly to an employee.
                                
                                --- COMPANY HR POLICY ---
                                {policy_text}
                                
                                --- EMPLOYEE CONTEXT (The person you are talking to) ---
                                Name: {emp['name']}
                                Department: {emp['department']}
                                Designation: {emp['designation']}
                                Join Date: {emp['join_date']}
                                Current Leave Balance: {emp['leave_balance']} days
                                
                                --- USER QUESTION ---
                                {user_question}
                                
                                Instructions:
                                1. Answer the user's question directly and concisely.
                                2. If they ask about themselves (like their balance), use the Employee Context to answer.
                                3. If they ask about rules, use the Company HR Policy.
                                4. Do not make up any policies that are not in the provided text.
                                5. Be polite and helpful.
                                """
                                
                                # Call Gemini
                                response = gemini_client.models.generate_content(
                                    model='gemini-2.5-flash',
                                    contents=prompt
                                )
                                bot_reply = response.text
                                
                                st.markdown(bot_reply)
                                st.session_state['chat_history'].append({"role": "assistant", "content": bot_reply})
                                
                            except Exception as e:
                                st.error(f"Error communicating with Gemini AI: {str(e)}")
                
    conn.close()

def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if st.session_state['logged_in']:
        with st.sidebar:
            st.write(f"Logged in as: **{st.session_state['username']}** ({st.session_state['role']})")
            if st.button("Logout"):
                st.session_state.clear()
                st.rerun()

    if not st.session_state['logged_in']:
        display_login()
    else:
        if st.session_state['role'] == 'HR':
            display_hr_dashboard()
        else:
            display_employee_dashboard()

if __name__ == '__main__':
    main()
