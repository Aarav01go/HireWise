a# HireWise

An AI-powered HR Management System built for the Digital AI project (P_196).

## What it does

- Core HR: employee records, login (HR/Employee roles), leave management
- AI HR chatbot with policy Q&A
- AI resume screening and ranking
- Attrition prediction (optional, time permitting)

## Stack

Python, Streamlit, SQLite, Google Gemini API (free tier via AI Studio), pandas, scikit-learn.

## Setup

1. `python -m venv venv` then activate it
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and add your Gemini API key
4. `python test_gemini.py` to confirm the API key works
5. `python setup_db.py` to create the database
6. `streamlit run app.py` to launch

## Logins (dummy data)

- HR: `hr / hr123`
- Employee: `aarav / emp123`
