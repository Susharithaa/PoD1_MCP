import sqlite3
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

DB_PATH = "/app/db/demo.db"
app = FastAPI(title="Employee API", version="1.0")

class Employee(BaseModel):
    employee_id: int
    name: str
    department: str
    designation: str
    location: str

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/health")
def health():
    return {"status": "ok", "service": "employee_api"}

@app.get("/employees/count")
def count_employees(department: str | None = None):
    conn = get_conn()
    if department:
        row = conn.execute(
            "SELECT COUNT(*) as count FROM employees WHERE lower(department)=lower(?)",
            (department,)
        ).fetchone()
    else:
        row = conn.execute("SELECT COUNT(*) as count FROM employees").fetchone()
    conn.close()
    return {"count": row["count"], "department": department}

@app.get("/employees/{employee_id}")
def get_employee(employee_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM employees WHERE employee_id = ?", (employee_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")
    return dict(row)

@app.get("/employees")
def search_employees(
    department: str | None = Query(None),
    location: str | None = Query(None),
    designation: str | None = Query(None)
):
    query = "SELECT * FROM employees WHERE 1=1"
    params = []

    if department:
        query += " AND lower(department) = lower(?)"
        params.append(department)
    if location:
        query += " AND lower(location) = lower(?)"
        params.append(location)
    if designation:
        query += " AND lower(designation) = lower(?)"
        params.append(designation)

    conn = get_conn()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return {"count": len(rows), "employees": [dict(r) for r in rows]}

@app.post("/employees")
def add_employee(employee: Employee):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO employees VALUES (?, ?, ?, ?, ?)",
            (
                employee.employee_id,
                employee.name,
                employee.department,
                employee.designation,
                employee.location,
            )
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Employee already exists")
    finally:
        conn.close()

    return {"message": "Employee added", "employee": employee}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0", port=27017)
