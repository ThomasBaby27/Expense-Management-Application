from typing import List, Optional
from fastapi import FastAPI, Query, status, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import SQLModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Date
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import date, datetime, timedelta

app = FastAPI(title="Expense Management Application")

# this for the sqlite Integration but the time is not enough to  complete so i use the in memory storage for data
SQLALCHEMY_DATABASE_URL = "sqlite:///./expenses.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
base = declarative_base()

# using the in memory storage for data
expenses_db = []
id_count = 1
total_salary = 50000

class expensecreate(BaseModel):
    name: str
    amount: float
    category: str
    date: Optional[date] = None

class expenseResponse(BaseModel):
    expense_id: int
    name: str
    amount: float
    category: str
    date: date
    
class totalExpenseResponse(BaseModel):
    total_expense: float
    remaining_salary: float
    total_salary: float

# 1.2) this api for finding Expense
@app.post("/expenses/", response_model=expenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(expense: expensecreate):
    global id_count
    new_expense = {
        "expense_id": id_count,
        "name": expense.name,
        "amount": expense.amount,
        "category": expense.category,
        "date": expense.date or date.today()
    }
    expenses_db.append(new_expense)
    id_count += 1
    return new_expense

# 1.3) this api for getting all Expenses
@app.get("/expenses/", response_model=List[expenseResponse], status_code=status.HTTP_200_OK)
def get_expenses():
    return expenses_db

# 1.4) this api for filtering ecpense by month
@app.get("/expenses/month/{year}/{month}/", response_model=List[expenseResponse], status_code=status.HTTP_200_OK)
def filter_by_month(year: int, month: int):
    filtered_expenses = [expense for expense in expenses_db if expense["date"].year == year and expense["date"].month == month]
    return filtered_expenses


# 1.5) this api for getting total expense
@app.get("/total/", response_model=totalExpenseResponse, status_code=status.HTTP_200_OK)
def get_total_expenses(salary: Optional[float] = Query(None)):
    current_salary = salary if salary is not None else total_salary
    total_expense = sum(expense["amount"] for expense in expenses_db)
    remaining_salary = current_salary - total_expense
    return totalExpenseResponse(
        total_expense=total_expense,
        remaining_salary=remaining_salary,
        total_salary=current_salary
    )
    
