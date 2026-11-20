# Expense Management Application (Round 2)

A resilient FastAPI backend for expense tracking, powered by SQLAlchemy ORM with Optimistic Concurrency Control (OCC) and dynamic database support.

---

## Setup & Running Locally

### 1. Environment Setup
```bash
# Clone the repository and navigate into the project directory
cd paywint

# Create and activate virtual environment
python -m venv env

# Windows PowerShell:
.\env\Scripts\Activate.ps1
# Linux/macOS:
source env/bin/activate

# Install dependencies
pip install -r requirements.txt

Run with SQLite
uvicorn main:app --reload --port 8000

API documentation:  http://127.0.0.1:8000/docs

Concurrency & Conflict Model

Optimistic Concurrency Control (OCC): Every record includes an integer version field.

Atomic Version Match: When updating via PUT /expenses/{expense_id}/, the client provides the last known version. The update runs atomically
UPDATE expenses
SET name = :name, amount = :amount, category = :category, date = :date, version = version + 1
WHERE expense_id = :id AND version = :expected_version;
If zero rows are affected, a race condition occurred. The server rejects the stale update with 409 Conflict, avoiding silent overwrites.

Resilience: Unhandled operational and lock errors trigger a clean rollback and return 503 Service Unavailable with Retry-After: 2.
