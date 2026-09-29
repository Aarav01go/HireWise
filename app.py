import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import os
from dotenv import load_dotenv
from google import genai
from pypdf import PdfReader
import joblib

# ==========================================
# 1. INITIALIZATION & CONFIGURATION
# ==========================================

# Load environment variables (pulls the GEMINI_API_KEY from the .env file)
load_dotenv()

# Initialize the Google Gemini AI client
try:
    gemini_client = genai.Client()
except Exception:
    gemini_client = None

# Configure the Streamlit page aesthetics
st.set_page_config(page_title="HireWise HRMS", page_icon="🏢", layout="wide")


# ==========================================
# 2. DATABASE HELPER FUNCTIONS
# ==========================================

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect('hrms.db')
    # This allows us to access columns by name (e.g. row['name'])
    conn.row_factory = sqlite3.Row
    return conn

def login_user(username, password):
    """Checks if the provided username and password match our database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # Note: Passwords are in plain text here for simplicity. 
    # In a real app, you would hash them!
    cursor.execute("SELECT * FROM users WHERE username=? AND password_hash=?", (username, password))
    user = cursor.fetchone()
    conn.close()
    return user


# ==========================================
# 3. LOGIN PAGE
# ==========================================

def display_login():
    """Renders the login screen if the user is not authenticated."""
    st.title("🏢 Welcome to HireWise")
    st.subheader("Please Login")
    
    # We use a form so the page doesn't refresh on every single keystroke
    with st.form("login_form"):
        username = st.text_input("Username", autocomplete="new-password")
        password = st.text_input("Password", type="password", autocomplete="new-password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            user = login_user(username, password)
            if user:
                # Store user details in session memory so Streamlit remembers them
                st.session_state['logged_in'] = True
                st.session_state['username'] = user['username']
                st.session_state['role'] = user['role']
                st.session_state['employee_id'] = user['employee_id']
                st.success("Logged in successfully!")
                st.rerun() # Refresh page to show the dashboard
            else:
                st.error("Invalid Username or Password")


# ==========================================
# 4. HR DASHBOARD
# ==========================================

def display_hr_dashboard():
    """Renders the master dashboard exclusively for HR Managers."""
    st.title("👥 HR Dashboard")
    
    # Break the dashboard into 5 distinct workspaces
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "View Employees", 
        "Add New Employee", 
        "Leave Requests", 
        "🧠 AI Resume Screening", 
        "🔮 Attrition Prediction"
    ])
    
    # --- TAB 1: EMPLOYEE DIRECTORY ---
    with tab1:
        st.subheader("Employee Records")
        conn = get_db_connection()
        # Fetch everyone and display them in a neat pandas dataframe
        df = pd.read_sql_query("SELECT id, name, email, department, designation, join_date, salary, leave_balance FROM employees", conn)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
    # --- TAB 2: ADD NEW EMPLOYEE ---
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
                    cursor = conn.cursor()
                    try:
                        # Insert the new employee into the DB
                        cursor.execute('''
                        INSERT INTO employees (name, email, department, designation, join_date, salary, leave_balance)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (name, email, department, designation, join_date.strftime('%Y-%m-%d'), salary, leave_balance))
                        conn.commit()
                        st.success(f"Employee {name} added successfully!")
                    except sqlite3.IntegrityError:
                        st.error("An employee with this email already exists.")
                else:
                    st.error("Please fill in all required fields.")
                    
    # --- TAB 3: LEAVE MANAGEMENT (HR VIEW) ---
    with tab3:
        st.subheader("Pending Leave Requests")
        cursor = conn.cursor()
        
        # We use a JOIN here to get the actual name of the employee, not just their ID number
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
                # Create a clickable dropdown for each request
                with st.expander(f"{leave['name']} - {leave['leave_type']} ({leave['start_date']} to {leave['end_date']})"):
                    st.write(f"**Applied on:** {leave['applied_on']}")
                    st.write(f"**Reason:** {leave['reason']}")
                    
                    col1, col2 = st.columns(2)
                    # APPROVAL LOGIC
                    with col1:
                        if st.button("✅ Approve", key=f"approve_{leave['id']}"):
                            # Calculate exact days off
                            start = datetime.strptime(leave['start_date'], '%Y-%m-%d')
                            end = datetime.strptime(leave['end_date'], '%Y-%m-%d')
                            days_taken = (end - start).days + 1
                            
                            # Mark as approved and deduct the days from their balance
                            cursor.execute("UPDATE leaves SET status='Approved' WHERE id=?", (leave['id'],))
                            cursor.execute("UPDATE employees SET leave_balance = leave_balance - ? WHERE name=?", (days_taken, leave['name']))
                            conn.commit()
                            st.success("Leave Approved!")
                            st.rerun()
                            
                    # REJECTION LOGIC
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
        
    # --- TAB 4: AI RESUME SCREENING ---
    with tab4:
        st.subheader("🧠 AI Resume Screening")
        st.write("Upload a Job Description and candidate resumes (PDFs). The AI will score them out of 100.")
        
        job_description = st.text_area("Job Description / Requirements", height=150, placeholder="Paste the job description here...")
        uploaded_files = st.file_uploader("Upload Resumes (PDF only)", type="pdf", accept_multiple_files=True)
        
        if st.button("Screen Resumes"):
            if not gemini_client:
                st.error("Gemini API Client is not initialized. Please check your .env file and API key.")
            elif not job_description or not uploaded_files:
                st.warning("Please provide both a Job Description and at least one resume.")
            else:
                with st.spinner("Analyzing resumes... This may take a minute."):
                    results = []
                    for uploaded_file in uploaded_files:
                        try:
                            # 1. Read the PDF file
                            reader = PdfReader(uploaded_file)
                            resume_text = ""
                            for page in reader.pages:
                                text = page.extract_text()
                                if text:
                                    resume_text += text + "\n"
                                    
                            # 2. Build the AI Prompt
                            prompt = f"""
                            You are an expert HR Recruiter. 
                            I will provide you with a Job Description and a Candidate's Resume.
                            
                            JOB DESCRIPTION:
                            {job_description}
                            
                            CANDIDATE RESUME:
                            {resume_text}
                            
                            TASK:
                            1. Score the resume from 0 to 100 based on how well it matches the Job Description.
                            2. Provide a short 2-3 sentence reason for the score, highlighting key matches or missing skills.
                            
                            FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
                            Score: [Number]
                            Reason: [Your reason]
                            """
                            
                            # 3. Call the Gemini API
                            response = gemini_client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=prompt
                            )
                            
                            results.append({
                                "File Name": uploaded_file.name,
                                "AI Feedback": response.text
                            })
                            
                        except Exception as e:
                            st.error(f"Error processing {uploaded_file.name}: {str(e)}")
                            
                    st.success("Screening Complete!")
                    for res in results:
                        with st.expander(f"Candidate: {res['File Name']}", expanded=True):
                            st.write(res['AI Feedback'])

    # --- TAB 5: ML ATTRITION PREDICTION ---
    with tab5:
        st.subheader("🔮 ML Attrition Prediction")
        st.write("Predict the likelihood of an employee resigning based on historical IBM HR data.")
        
        try:
            # Load the frozen "brain" we created with train_model.py
            model = joblib.load('attrition_model.pkl')
            
            with st.form("attrition_form"):
                col1, col2 = st.columns(2)
                with col1:
                    age = st.number_input("Employee Age", min_value=18, max_value=80, value=30)
                    income = st.number_input("Monthly Income ($)", min_value=1000, value=5000, step=500)
                    years = st.number_input("Years at Company", min_value=0, max_value=50, value=2)
                with col2:
                    satisfaction = st.slider("Job Satisfaction (1=Low, 4=Very High)", 1, 4, 3)
                    overtime = st.selectbox("Does the employee work overtime?", ["No", "Yes"])
                
                submitted = st.form_submit_button("Predict Attrition")
                if submitted:
                    # Map the Overtime text into a number just like we did during training
                    ot_val = 1 if overtime == "Yes" else 0
                    
                    # Create a mini dataframe matching the shape of our training data
                    input_data = pd.DataFrame([[age, income, satisfaction, ot_val, years]], 
                                              columns=['Age', 'MonthlyIncome', 'JobSatisfaction', 'OverTime', 'YearsAtCompany'])
                    
                    # Ask the model for the probability of class 1 (Quitting)
                    probability = model.predict_proba(input_data)[0][1]
                    percent = round(probability * 100, 1)
                    
                    # Give actionable HR advice based on the risk percentage
                    if percent > 50:
                        st.error(f"⚠️ **High Risk of Flight:** {percent}% chance this employee will resign.")
                        st.write("Suggestion: Schedule a 1-on-1, review compensation, or check workload (overtime).")
                    elif percent > 25:
                        st.warning(f"🟡 **Moderate Risk:** {percent}% chance this employee will resign.")
                        st.write("Suggestion: Monitor job satisfaction and ensure they are engaged.")
                    else:
                        st.success(f"✅ **Low Risk:** {percent}% chance this employee will resign.")
                        
        except FileNotFoundError:
            st.error("Model file 'attrition_model.pkl' not found. Please run 'python train_model.py' first.")
            
    conn.close()


# ==========================================
# 5. EMPLOYEE DASHBOARD
# ==========================================

def display_employee_dashboard():
    """Renders the dashboard for standard employees."""
    st.title("👋 Employee Portal")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    # Fetch just the logged-in employee's data
    cursor.execute("SELECT * FROM employees WHERE id=?", (st.session_state['employee_id'],))
    emp = cursor.fetchone()
    
    if emp:
        # --- PROFILE HEADER ---
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
        
        # --- TAB 1: APPLY FOR LEAVE ---
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
                        # Make sure they have enough days (unless it's unpaid)
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
                            
        # --- TAB 2: LEAVE HISTORY ---
        with tab2:
            st.subheader("📖 Leave History")
            # Only show leaves that belong to this specific employee
            df = pd.read_sql_query("SELECT leave_type, start_date, end_date, reason, status, applied_on FROM leaves WHERE employee_id=?", conn, params=(emp['id'],))
            if df.empty:
                st.write("You haven't applied for any leaves yet.")
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)
                
        # --- TAB 3: HR CHATBOT (RAG) ---
        with tab3:
            st.subheader("🤖 AI HR Assistant")
            st.info("I am an AI assistant integrated with Gemini. Ask me about company policy or your personal leave balance!")
            
            # Setup a temporary memory array in session_state to hold the chat bubbles
            if 'chat_history' not in st.session_state:
                st.session_state['chat_history'] = []
                
            # Draw the past messages
            for msg in st.session_state['chat_history']:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    
            # The input box where they type
            user_question = st.chat_input("E.g. What is the notice period? or How many leaves do I have?")
            
            if user_question:
                # Add what the user just typed to the screen
                st.session_state['chat_history'].append({"role": "user", "content": user_question})
                with st.chat_message("user"):
                    st.markdown(user_question)
                    
                with st.chat_message("assistant"):
                    if not gemini_client:
                        st.error("Gemini API Client is not initialized. Please check your .env file and API key.")
                    else:
                        with st.spinner("Looking up HR Policies..."):
                            try:
                                # RAG Step 1: Read the Knowledge Base
                                policy_text = ""
                                try:
                                    with open("docs/hr_policy.txt", "r") as f:
                                        policy_text = f.read()
                                except FileNotFoundError:
                                    policy_text = "No HR policy document found."
                                
                                # RAG Step 2: Build the Super Prompt
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
                                
                                # RAG Step 3: Ask the AI
                                response = gemini_client.models.generate_content(
                                    model='gemini-2.5-flash',
                                    contents=prompt
                                )
                                bot_reply = response.text
                                
                                # Print the AI's reply and save it to history
                                st.markdown(bot_reply)
                                st.session_state['chat_history'].append({"role": "assistant", "content": bot_reply})
                                
                            except Exception as e:
                                st.error(f"Error communicating with Gemini AI: {str(e)}")
                
    conn.close()


# ==========================================
# 6. APP ROUTER
# ==========================================

def main():
    """Main routing function that decides which screen to show."""
    
    # Ensure our login tracker exists
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    # If they are logged in, draw the sidebar with the logout button
    if st.session_state['logged_in']:
        with st.sidebar:
            st.write(f"Logged in as: **{st.session_state['username']}** ({st.session_state['role']})")
            if st.button("Logout"):
                st.session_state.clear()
                st.rerun()

    # Route traffic based on role
    if not st.session_state['logged_in']:
        display_login()
    else:
        if st.session_state['role'] == 'HR':
            display_hr_dashboard()
        else:
            display_employee_dashboard()


# Starts the app
if __name__ == '__main__':
    main()
