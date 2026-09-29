import streamlit as st
import sqlite3
import pandas as pd

st.set_page_config(page_title="HRMS Dashboard", page_icon="🏢")

st.title("Welcome to P_196 - HRMS! 🚀")
st.write("This is a simple Streamlit app connecting to our SQLite database.")

# Function to get data from a table
def load_data(table_name):
    conn = sqlite3.connect('hrms.db')
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

st.header("Database Overview")

# Load and display all tables in tabs
tab1, tab2, tab3 = st.tabs(["Employees", "Users", "Leaves"])

with tab1:
    st.subheader("Employees Table")
    try:
        employees_df = load_data("employees")
        st.dataframe(employees_df, use_container_width=True)
    except Exception as e:
        st.error(f"Error loading employees: {e}")

with tab2:
    st.subheader("Users Table")
    try:
        users_df = load_data("users")
        st.dataframe(users_df, use_container_width=True)
    except Exception as e:
        st.error(f"Error loading users: {e}")

with tab3:
    st.subheader("Leaves Table")
    try:
        leaves_df = load_data("leaves")
        st.dataframe(leaves_df, use_container_width=True)
    except Exception as e:
        st.error(f"Error loading leaves: {e}")

st.success("Day 1 Setup Complete! Database and UI are connected.")
