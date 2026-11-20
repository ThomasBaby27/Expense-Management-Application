import datetime as dt
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExpenseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0, le=10_000_000)
    category: str = Field(..., min_length=2, max_length=50)
    date: Optional[dt.date] = None

    @field_validator("name", "category")
    @classmethod
    def strip_and_clean(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace.")
        return v

    @field_validator("category")
    @classmethod
    def clean_category(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return round(v, 2)

    @field_validator("date")
    @classmethod
    def validate_date_range(cls, v: Optional[dt.date]) -> Optional[dt.date]:
        if v is not None:
            min_date = dt.date(2000, 1, 1)
            max_date = dt.date.today() + dt.timedelta(days=365)
            if v < min_date or v > max_date:
                raise ValueError(f"Date must be between {min_date} and {max_date}.")
        return v


class ExpenseUpdate(ExpenseCreate):
    version: int = Field(..., ge=1, description="Expected version for optimistic locking")


class ExpenseResponse(BaseModel):
    expense_id: int
    name: str
    amount: float
    category: str
    date: dt.date
    version: int

    model_config = ConfigDict(from_attributes=True)


class TotalExpenseResponse(BaseModel):
    total_expense: float
    remaining_salary: float
    total_salary: float


# Consistent Error Envelope Models
class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    details: Optional[List[ErrorDetail]] = None


class StandardErrorResponse(BaseModel):
    error: ErrorBody