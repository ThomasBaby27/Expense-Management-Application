import calendar
import datetime as dt
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.exceptions import ConcurrencyConflictError, ExpenseNotFoundError
from app.models import ExpenseModel
from app.schemas import ExpenseCreate, ExpenseUpdate


def create_expense(db: Session, payload: ExpenseCreate) -> ExpenseModel:
    db_expense = ExpenseModel(
        name=payload.name,
        amount=payload.amount,
        category=payload.category,
        date=payload.date or dt.date.today(),
        version=1,
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense


def update_expense(db: Session, expense_id: int, payload: ExpenseUpdate) -> ExpenseModel:
    existing = db.query(ExpenseModel).filter(ExpenseModel.expense_id == expense_id).first()
    if not existing:
        raise ExpenseNotFoundError(expense_id=expense_id)

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
                "category": payload.category,
                "date": updated_date,
                "version": ExpenseModel.version + 1,
            },
            synchronize_session="fetch",
        )
    )

    if result == 0:
        db.rollback()
        raise ConcurrencyConflictError()

    db.commit()
    return db.query(ExpenseModel).filter(ExpenseModel.expense_id == expense_id).first()


def get_all_expenses(db: Session) -> List[ExpenseModel]:
    return db.query(ExpenseModel).order_by(ExpenseModel.date.desc(), ExpenseModel.expense_id.desc()).all()


def get_expenses_by_month(db: Session, year: int, month: int) -> List[ExpenseModel]:
    _, last_day = calendar.monthrange(year, month)
    start_date = dt.date(year, month, 1)
    end_date = dt.date(year, month, last_day)

    return (
        db.query(ExpenseModel)
        .filter(ExpenseModel.date >= start_date, ExpenseModel.date <= end_date)
        .order_by(ExpenseModel.date.asc(), ExpenseModel.expense_id.asc())
        .all()
    )


def compute_total_expenses(db: Session) -> float:
    total_val = db.query(func.coalesce(func.sum(ExpenseModel.amount), 0.0)).scalar()
    return round(float(total_val), 2)