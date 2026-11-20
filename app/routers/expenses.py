from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app import crud
from app.config import settings
from app.database import get_db
from app.schemas import (
    ExpenseCreate,
    ExpenseResponse,
    ExpenseUpdate,
    TotalExpenseResponse,
)

router = APIRouter(tags=["Expenses"])


@router.post(
    "/expenses/",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_expense(payload: ExpenseCreate, db: Session = Depends(get_db)):
    return crud.create_expense(db=db, payload=payload)


@router.put(
    "/expenses/{expense_id}/",
    response_model=ExpenseResponse,
    status_code=status.HTTP_200_OK,
)
def modify_expense(
    expense_id: int = Path(..., ge=1, description="Valid ID must be positive"),
    payload: ExpenseUpdate = ...,
    db: Session = Depends(get_db),
):
    return crud.update_expense(db=db, expense_id=expense_id, payload=payload)


@router.get(
    "/expenses/",
    response_model=List[ExpenseResponse],
    status_code=status.HTTP_200_OK,
)
def list_expenses(db: Session = Depends(get_db)):
    return crud.get_all_expenses(db=db)


@router.get(
    "/expenses/month/{year}/{month}/",
    response_model=List[ExpenseResponse],
    status_code=status.HTTP_200_OK,
)
def filter_expenses_by_month(
    year: int = Path(..., ge=2000, le=2100, description="Year between 2000 and 2100"),
    month: int = Path(..., ge=1, le=12, description="Month between 1 and 12"),
    db: Session = Depends(get_db),
):
    return crud.get_expenses_by_month(db=db, year=year, month=month)


@router.get(
    "/total/",
    response_model=TotalExpenseResponse,
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/totals/",
    response_model=TotalExpenseResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def calculate_totals(
    salary: Optional[float] = Query(None, gt=0, le=100_000_000, description="Base salary"),
    db: Session = Depends(get_db),
):
    current_salary = salary if salary is not None else settings.DEFAULT_SALARY
    total_val = crud.compute_total_expenses(db=db)
    remaining_salary = round(current_salary - total_val, 2)

    return TotalExpenseResponse(
        total_expense=total_val,
        remaining_salary=remaining_salary,
        total_salary=current_salary,
    )
