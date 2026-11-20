import calendar
import datetime as dt
import os
from typing import List, Optional
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from fastapi import Depends, FastAPI, HTTPException, Path, Query, status
from sqlalchemy import (
    Column,
    Date as SQLDate,
    Float,
    Index,
    Integer,
    String,
    create_engine,
    func,
)
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, sessionmaker
app = FastAPI(title="Expense Management Application")

# ---------------------------------------------------------------------------
# Database Configuration
# Defaults to SQLite, but can be switched via the DATABASE_URL environment
# variable (e.g. export DATABASE_URL="postgresql://user:pass@localhost/dbname")
# ---------------------------------------------------------------------------
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./expenses.db")

connect_args = (
    {"check_same_thread": False}
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ---------------------------------------------------------------------------
# SQLAlchemy Model
# ---------------------------------------------------------------------------
class ExpenseModel(Base):
    __tablename__ = "expenses"

    expense_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False, index=True)
    date = Column(SQLDate, nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)

    __table_args__ = (
        Index("idx_expenses_date_category", "date", "category"),
    )


# Automatically create the table on startup if it does not exist
Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Dependency for DB Session
# ---------------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# Global Exception Handler for Database Busy / Unavailability (HTTP 503)
# ---------------------------------------------------------------------------
@app.exception_handler(OperationalError)
async def db_operational_error_handler(request, exc: OperationalError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        headers={"Retry-After": "2"},
        content={
            "detail": "Database is temporarily busy or unavailable. Please retry your request shortly."
        },
    )

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
total_salary = 50000.0


class expensecreate(BaseModel):
    name: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    category: str = Field(..., min_length=1)
    date: Optional[dt.date] = None


class expenseUpdate(BaseModel):
    name: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    category: str = Field(..., min_length=1)
    date: Optional[dt.date] = None
    version: int = Field(..., description="The current version of the expense before update")


class expenseResponse(BaseModel):
    expense_id: int
    name: str
    amount: float
    category: str
    date: dt.date
    version: int

    model_config = ConfigDict(from_attributes=True)


class totalExpenseResponse(BaseModel):
    total_expense: float
    remaining_salary: float
    total_salary: float


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

# POST /expenses/
@app.post("/expenses/", response_model=expenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(expense: expensecreate, db: Session = Depends(get_db)):
    try:
        db_expense = ExpenseModel(
            name=expense.name,
            amount=expense.amount,
            category=expense.category.lower().strip(),
            date=expense.date if expense.date is not None else dt.date.today(),
            version=1,
        )
        db.add(db_expense)
        db.commit()
        db.refresh(db_expense)
        return db_expense
    except OperationalError:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record expense due to a storage error.",
        )
        
# PUT /expenses/{expense_id}/ (Concurrent Update with OCC)
@app.put("/expenses/{expense_id}/", response_model=expenseResponse, status_code=status.HTTP_200_OK)
def update_expense(
    expense_id: int,
    payload: expenseUpdate,
    db: Session = Depends(get_db),
):
    """
    Atomic update preventing concurrent overwrites:
    1. Checks if expense exists.
    2. Atomically increments version where expense_id and version match.
    3. Rejects stale writes with HTTP 409 Conflict.
    """
    try:
        # Check if record exists
        existing = db.query(ExpenseModel).filter(ExpenseModel.expense_id == expense_id).first()
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Expense with id {expense_id} not found.",
            )

        # Atomic update checking version match
        updated_date = payload.date if payload.date is not None else existing.date
        result = (
            db.query(ExpenseModel)
            .filter(
                ExpenseModel.expense_id == expense_id,
                ExpenseModel.version == payload.version,
            )
            .update(
                {
                    "name": payload.name,
                    "amount": payload.amount,
                    "category": payload.category.lower().strip(),
                    "date": updated_date,
                    "version": ExpenseModel.version + 1,
                },
                synchronize_session="fetch",
            )
        )

        # If 0 rows updated, a race condition occurred (another client committed first)
        if result == 0:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflict: This expense was modified by another client. Please fetch the latest version and retry.",
            )

        db.commit()

        # Reload updated record
        updated_expense = db.query(ExpenseModel).filter(ExpenseModel.expense_id == expense_id).first()
        return updated_expense

    except HTTPException:
        raise
    except OperationalError:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transaction failed and was safely rolled back.",
        )


# GET /expenses/
@app.get("/expenses/", response_model=List[expenseResponse], status_code=status.HTTP_200_OK)
def get_expenses(db: Session = Depends(get_db)):
    return db.query(ExpenseModel).order_by(ExpenseModel.date.desc(), ExpenseModel.expense_id.desc()).all()

# GET /expenses/month/{year}/{month}/
@app.get("/expenses/month/{year}/{month}/", response_model=List[expenseResponse], status_code=status.HTTP_200_OK)
def filter_by_month(
    year: int = Path(..., ge=1970, le=2100),
    month: int = Path(..., ge=1, le=12),
    db: Session = Depends(get_db),
):
    _, last_day = calendar.monthrange(year, month)
    start_date = dt.date(year, month, 1)
    end_date = dt.date(year, month, last_day)

    return (
        db.query(ExpenseModel)
        .filter(ExpenseModel.date >= start_date, ExpenseModel.date <= end_date)
        .order_by(ExpenseModel.date.asc(), ExpenseModel.expense_id.asc())
        .all()
    )


# GET /total/ and alias GET /totals/
@app.get("/total/", response_model=totalExpenseResponse, status_code=status.HTTP_200_OK)
@app.get("/totals/", response_model=totalExpenseResponse, status_code=status.HTTP_200_OK, include_in_schema=False)
def get_total_expenses(salary: Optional[float] = Query(None), db: Session = Depends(get_db)):
    current_salary = salary if salary is not None else total_salary

    total_val = db.query(func.coalesce(func.sum(ExpenseModel.amount), 0.0)).scalar()
    total_val = round(float(total_val), 2)
    remaining_salary = round(current_salary - total_val, 2)

    return totalExpenseResponse(
        total_expense=total_val,
        remaining_salary=remaining_salary,
        total_salary=current_salary,
    )