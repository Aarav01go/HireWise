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
# INITIALIZATION & CONFIGURATION
# ==========================================
load_dotenv()

try:
    gemini_client = genai.Client()
except Exception:
    gemini_client = None

st.set_page_config(page_title="HireWise HRMS", page_icon=":material/hexagon:", layout="wide")

# ==========================================
# DATABASE HELPERS
# ==========================================
def get_db_connection():
    # Make sure we connect to the database in the root folder
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

# ==========================================
# LOGIN PAGE (Brave-Safe)
# ==========================================
def display_login():
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.container(border=True):
            st.title(":material/hexagon: HireWise")
            st.markdown("### Welcome Back")
            st.caption("Sign in to your HR or Employee portal")
            st.divider()
            
            if 'login_username' not in st.session_state:
                st.session_state['login_username'] = ''
            if 'login_password' not in st.session_state:
                st.session_state['login_password'] = ''
            
            st.session_state['login_username'] = st.text_input(
                "Username", value=st.session_state['login_username'], autocomplete="off", key="login_user_input"
            )
            st.session_state['login_password'] = st.text_input(
                "Password", type="password", value=st.session_state['login_password'], autocomplete="off", key="login_pass_input"
            )
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Login", type="primary", use_container_width=True):
                username = st.session_state['login_username']
                password = st.session_state['login_password']
                if not username or not password:
                    st.warning("Please enter both username and password.")
                else:
                    user = login_user(username, password)
                    if user:
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = user['username']
                        st.session_state['role'] = user['role']
                        st.session_state['employee_id'] = user['employee_id']
                        del st.session_state['login_username']
                        del st.session_state['login_password']
                        st.rerun()
                    else:
                        st.error("Invalid Username or Password")

# ==========================================
# HR DASHBOARD (DRIBBBLE-STYLE)
# ==========================================
def display_hr_dashboard():
    # --- SIDEBAR NAV ---
    with st.sidebar:
        st.markdown("## :material/hexagon: HireWise")
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.caption("NAVIGATION")
        active_view = st.radio(
            "Menu", 
            ["Dashboard", "Employees", "Leave Requests", "AI Resume Screening", "Attrition ML"], 
            label_visibility="collapsed"
        )
        
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.write(f"🧔🏽‍♀️ **{st.session_state['username']}** ({st.session_state['role']})")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()

    conn = get_db_connection()

    # --- VIEW: DASHBOARD ---
    if active_view == "Dashboard":
        header_col1, header_col2 = st.columns([8, 2])
        with header_col1:
            st.title("Dashboard")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Calculate real metrics
        cursor = conn.cursor()
        total_employees = cursor.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
        pending_leaves = cursor.execute("SELECT COUNT(*) FROM leaves WHERE status='Pending'").fetchone()[0]
        
        # KPI CARDS
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            with st.container(border=True):
                st.markdown("**Total Employees**")
                st.markdown(f"### :material/groups: {total_employees}")
        with kpi2:
            with st.container(border=True):
                st.markdown("**Pending Leaves**")
                st.markdown(f"### :material/event_note: {pending_leaves}")
        with kpi3:
            with st.container(border=True):
                st.markdown("**Avg Salary**")
                avg_sal = cursor.execute("SELECT AVG(salary) FROM employees").fetchone()[0]
                avg_sal = avg_sal if avg_sal else 0
                st.markdown(f"### :material/payments: ${avg_sal:,.0f}")
                
        st.markdown("<br>", unsafe_allow_html=True)
        
        # SPLIT VIEW
        left_col, right_col = st.columns([6, 4], gap="large")
        with left_col:
            with st.container(border=True):
                st.markdown("#### Department Headcount")
                dept_df = pd.read_sql_query("SELECT department as Department, COUNT(*) as Count FROM employees GROUP BY department", conn)
                if not dept_df.empty:
                    st.bar_chart(dept_df, x="Department", y="Count", color="#E88C6B", height=250)
                else:
                    st.info("No data yet.")
        with right_col:
            with st.container(border=True):
                st.markdown("#### Upcoming Action Items")
                if pending_leaves > 0:
                    st.markdown(f"**• {pending_leaves} Pending Leave Requests**")
                    st.caption("Requires HR Approval")
                else:
                    st.write("No pending leaves!")
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("**• Run Payroll**")
                st.caption("End of month")
                
    # --- VIEW: EMPLOYEES ---
    elif active_view == "Employees":
        st.title("Employees")
        
        tab1, tab2, tab3 = st.tabs(["Directory", "Add Employee", "AI Performance Reviews"])
        
        with tab1:
            with st.container(border=True):
                st.markdown("#### Company Directory")
                
                # Smart Filters
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    search_name = st.text_input("Search by Name", placeholder="e.g. Aarav", label_visibility="collapsed")
                with col_f2:
                    depts = pd.read_sql_query("SELECT DISTINCT department FROM employees", conn)['department'].tolist()
                    filter_dept = st.multiselect("Filter by Department", depts, placeholder="Select Departments...", label_visibility="collapsed")
                
                # Build the query based on filters
                query = "SELECT id, name, email, department, designation, join_date, salary, leave_balance FROM employees WHERE 1=1"
                params = []
                if search_name:
                    query += " AND name LIKE ?"
                    params.append(f"%{search_name}%")
                if filter_dept:
                    placeholders = ",".join(["?"] * len(filter_dept))
                    query += f" AND department IN ({placeholders})"
                    params.extend(filter_dept)
                    
                df = pd.read_sql_query(query, conn, params=params)
                
                st.caption("Tip: You can edit Department, Designation, Salary, and Leave Balance directly in the table!")
                
                # ENHANCED & EDITABLE TABLE VIEW
                edited_df = st.data_editor(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    disabled=["id", "name", "email", "join_date"], # Lock personal details
                    column_config={
                        "id": st.column_config.TextColumn("ID"),
                        "name": st.column_config.TextColumn("Name"),
                        "email": st.column_config.TextColumn("Email"),
                        "department": st.column_config.SelectboxColumn("Dept", options=depts),
                        "salary": st.column_config.NumberColumn("Salary", format="$%d"),
                        "leave_balance": st.column_config.NumberColumn("Leave Balance")
                    }
                )
                
                # Save button for inline edits
                if st.button("💾 Save Table Changes", type="primary"):
                    cursor = conn.cursor()
                    for index, row in edited_df.iterrows():
                        # Update the database with the edited row data
                        cursor.execute('''
                            UPDATE employees 
                            SET department=?, designation=?, salary=?, leave_balance=?
                            WHERE id=?
                        ''', (row['department'], row['designation'], row['salary'], row['leave_balance'], row['id']))
                    conn.commit()
                    st.success("Changes saved successfully!")
                    st.rerun()
                
        with tab2:
            with st.container(border=True):
                st.markdown("#### Onboard New Hire")
                with st.form("add_employee_form"):
                    name = st.text_input("Full Name")
                    email = st.text_input("Email")
                    department = st.selectbox("Department", ["HR", "Engineering", "Sales", "Marketing", "Finance"])
                    designation = st.text_input("Designation")
                    join_date = st.date_input("Join Date")
                    salary = st.number_input("Salary", min_value=0, step=1000)
                    leave_balance = st.number_input("Starting Leave Balance", min_value=0, value=20)
                    
                    if st.form_submit_button("Add Employee", type="primary"):
                        if name and email and designation:
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
                        else:
                            st.error("Please fill in all required fields.")
                            
        with tab3:
            with st.container(border=True):
                st.markdown("#### ✨ AI Performance Review Generator")
                st.write("Select an employee to instantly generate a draft performance review based on their role and tenure.")
                
                # Get list of employees for the dropdown
                emp_list = pd.read_sql_query("SELECT id, name, department, designation, join_date FROM employees", conn)
                selected_name = st.selectbox("Select Employee", emp_list['name'].tolist())
                
                if st.button("Generate Review", type="primary"):
                    if not gemini_client:
                        st.error("Gemini API Key missing.")
                    else:
                        with st.spinner(f"Writing review for {selected_name}..."):
                            # Get their specific data
                            emp_data = emp_list[emp_list['name'] == selected_name].iloc[0]
                            prompt = f"""
                            You are an expert HR Manager writing a positive, professional year-end performance review draft.
                            Employee Name: {emp_data['name']}
                            Role: {emp_data['designation']} in the {emp_data['department']} department.
                            Joined Company: {emp_data['join_date']}
                            
                            Write a 2-paragraph performance review. Highlight their dedication, suggest 1 generic area of growth, and end on an encouraging note.
                            """
                            res = gemini_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                            st.info(res.text)

    # --- VIEW: LEAVE REQUESTS ---
    elif active_view == "Leave Requests":
        st.title("Leave Requests")
        
        with st.container(border=True):
            st.markdown("#### Pending Approvals")
            cursor = conn.cursor()
            cursor.execute('''
                SELECT l.id, e.name, l.leave_type, l.start_date, l.end_date, l.reason, l.applied_on
                FROM leaves l
                JOIN employees e ON l.employee_id = e.id
                WHERE l.status = 'Pending'
            ''')
            pending = cursor.fetchall()
            
            if not pending:
                st.info("Inbox Zero! No pending requests.")
            else:
                for leave in pending:
                    with st.expander(f"{leave['name']} - {leave['leave_type']} ({leave['start_date']} to {leave['end_date']})"):
                        st.write(f"**Reason:** {leave['reason']}")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("✅ Approve", key=f"app_{leave['id']}", type="primary"):
                                start = datetime.strptime(leave['start_date'], '%Y-%m-%d')
                                end = datetime.strptime(leave['end_date'], '%Y-%m-%d')
                                days = (end - start).days + 1
                                cursor.execute("UPDATE leaves SET status='Approved' WHERE id=?", (leave['id'],))
                                cursor.execute("UPDATE employees SET leave_balance = leave_balance - ? WHERE name=?", (days, leave['name']))
                                conn.commit()
                                st.rerun()
                        with c2:
                            if st.button("❌ Reject", key=f"rej_{leave['id']}"):
                                cursor.execute("UPDATE leaves SET status='Rejected' WHERE id=?", (leave['id'],))
                                conn.commit()
                                st.rerun()
                                
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("#### Company Leave History")
            df = pd.read_sql_query("SELECT l.id, e.name, l.leave_type, l.start_date, l.end_date, l.status FROM leaves l JOIN employees e ON l.employee_id = e.id", conn)
            st.dataframe(df, use_container_width=True, hide_index=True)

    # --- VIEW: AI RESUME SCREENING ---
    elif active_view == "AI Resume Screening":
        st.title("AI Resume Screening")
        
        with st.container(border=True):
            st.markdown("#### 🧠 Evaluate Candidates")
            st.write("Upload a Job Description and candidate resumes (PDFs).")
            
            job_desc = st.text_area("Job Description", height=150)
            files = st.file_uploader("Upload Resumes (PDF)", type="pdf", accept_multiple_files=True)
            
            if st.button("Screen Resumes", type="primary"):
                if not gemini_client:
                    st.error("API Key missing.")
                elif not job_desc or not files:
                    st.warning("Provide JD and at least one PDF.")
                else:
                    with st.spinner("Analyzing..."):
                        for f in files:
                            reader = PdfReader(f)
                            text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
                            prompt = f"Role:\n{job_desc}\n\nResume:\n{text}\n\nScore 0-100 and give 2 sentences reason. Format: Score: [X]\nReason: [Y]"
                            res = gemini_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                            with st.expander(f"Result for {f.name}", expanded=True):
                                st.write(res.text)

    # --- VIEW: ATTRITION ML ---
    elif active_view == "Attrition ML":
        st.title("Attrition Prediction")
        
        with st.container(border=True):
            st.markdown("#### 🔮 Flight Risk Predictor")
            st.write("Predict likelihood of resignation.")
            try:
                model = joblib.load('attrition_model.pkl')
                with st.form("ml_form"):
                    c1, c2 = st.columns(2)
                    with c1:
                        age = st.number_input("Age", 18, 80, 30)
                        inc = st.number_input("Income ($)", 1000, value=5000)
                        yrs = st.number_input("Years at Co.", 0, 50, 2)
                    with c2:
                        sat = st.slider("Job Satisfaction", 1, 4, 3)
                        ot = st.selectbox("Overtime?", ["No", "Yes"])
                    
                    if st.form_submit_button("Predict", type="primary"):
                        ot_val = 1 if ot == "Yes" else 0
                        inp = pd.DataFrame([[age, inc, sat, ot_val, yrs]], columns=['Age', 'MonthlyIncome', 'JobSatisfaction', 'OverTime', 'YearsAtCompany'])
                        prob = model.predict_proba(inp)[0][1] * 100
                        if prob > 50:
                            st.error(f"⚠️ **High Risk:** {prob:.1f}%")
                        elif prob > 25:
                            st.warning(f"🟡 **Moderate Risk:** {prob:.1f}%")
                        else:
                            st.success(f"✅ **Low Risk:** {prob:.1f}%")
            except Exception as e:
                st.error("Model file not found. Run train_model.py first.")

    conn.close()

# ==========================================
# EMPLOYEE DASHBOARD
# ==========================================
def display_employee_dashboard():
    # --- SIDEBAR NAV ---
    with st.sidebar:
        st.markdown("## :material/hexagon: HireWise")
        st.markdown("<br>", unsafe_allow_html=True)
        menu = st.radio("Menu", ["Dashboard", "My Leave History", "AI Assistant"], label_visibility="collapsed")
        
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.write(f"🧔🏽‍♀️ **{st.session_state['username']}** ({st.session_state['role']})")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE id=?", (st.session_state['employee_id'],))
    emp = cursor.fetchone()
    
    if menu == "Dashboard":
        st.title("My Dashboard")
        
        c1, c2 = st.columns([7, 3])
        with c1:
            with st.container(border=True):
                st.markdown("#### Profile Details")
                st.write(f"**Name:** {emp['name']}")
                st.write(f"**Role:** {emp['designation']} ({emp['department']})")
                st.write(f"**Email:** {emp['email']}")
                
        with c2:
            with st.container(border=True):
                st.markdown("#### Leave Balance")
                st.markdown(f"## {emp['leave_balance']} days")
                
        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("#### Apply for Leave")
            with st.form("leave_form"):
                leave_type = st.selectbox("Type", ["Casual Leave", "Sick Leave", "Paid Leave", "Unpaid Leave"])
                sc1, sc2 = st.columns(2)
                with sc1: start_date = st.date_input("Start")
                with sc2: end_date = st.date_input("End")
                reason = st.text_area("Reason")
                
                if st.form_submit_button("Submit Application", type="primary"):
                    days = (end_date - start_date).days + 1
                    if end_date < start_date:
                        st.error("End date invalid.")
                    elif emp['leave_balance'] < days and leave_type != "Unpaid Leave":
                        st.error("Insufficient balance.")
                    else:
                        cursor.execute("INSERT INTO leaves (employee_id, leave_type, start_date, end_date, reason, status, applied_on) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                       (emp['id'], leave_type, start_date, end_date, reason, 'Pending', date.today()))
                        conn.commit()
                        st.success("Submitted successfully!")
                        st.rerun()

    elif menu == "My Leave History":
        st.title("Leave History")
        with st.container(border=True):
            df = pd.read_sql_query("SELECT leave_type, start_date, end_date, status FROM leaves WHERE employee_id=?", conn, params=(emp['id'],))
            st.dataframe(df, use_container_width=True, hide_index=True)

    elif menu == "AI Assistant":
        st.title("AI HR Assistant")
        with st.container(border=True):
            if 'chat_history' not in st.session_state:
                st.session_state['chat_history'] = []
            for msg in st.session_state['chat_history']:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            
            q = st.chat_input("Ask about policies or your balance...")
            if q:
                st.session_state['chat_history'].append({"role": "user", "content": q})
                with st.chat_message("user"): st.markdown(q)
                with st.chat_message("assistant"):
                    if not gemini_client:
                        st.error("API Key missing.")
                    else:
                        try:
                            with open("docs/hr_policy.txt", "r") as f: pol = f.read()
                        except: pol = ""
                        prompt = f"Policy:\n{pol}\n\nEmployee:\nName: {emp['name']}\nBalance: {emp['leave_balance']}\n\nQ: {q}"
                        res = gemini_client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                        st.markdown(res.text)
                        st.session_state['chat_history'].append({"role": "assistant", "content": res.text})

    conn.close()

# ==========================================
# APP ROUTER
# ==========================================
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        display_login()
    else:
        if st.session_state['role'] == 'HR':
            display_hr_dashboard()
        else:
            display_employee_dashboard()

if __name__ == '__main__':
    main()
