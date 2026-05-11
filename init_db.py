import sqlite3
from pathlib import Path

Path("db").mkdir(exist_ok=True)

conn = sqlite3.connect("db/demo.db")
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS employees")
cur.execute("DROP TABLE IF EXISTS salaries")

cur.execute("""
CREATE TABLE employees (
    employee_id INTEGER PRIMARY KEY,
    name TEXT,
    department TEXT,
    designation TEXT,
    location TEXT
)
""")

cur.execute("""
CREATE TABLE salaries (
    employee_id INTEGER PRIMARY KEY,
    monthly_salary INTEGER,
    currency TEXT,
    bonus INTEGER,
    effective_from TEXT
)
""")

cur.executemany("""
INSERT INTO employees VALUES (?, ?, ?, ?, ?)
""", [
    (101, "Ravi Kumar", "HR", "HR Manager", "Chennai"),
    (102, "Meena Iyer", "Finance", "Finance Analyst", "Bangalore"),
    (103, "Arjun Raj", "Engineering", "Lead Engineer", "Tokyo"),
    (104, "Priya Nair", "HR", "Recruiter", "Chennai")
])

cur.executemany("""
INSERT INTO salaries VALUES (?, ?, ?, ?, ?)
""", [
    (101, 85000, "INR", 10000, "2026-01-01"),
    (102, 120000, "INR", 15000, "2026-01-01"),
    (103, 750000, "JPY", 50000, "2026-01-01"),
    (104, 70000, "INR", 8000, "2026-01-01")
])

conn.commit()
conn.close()

print("DB created successfully")
