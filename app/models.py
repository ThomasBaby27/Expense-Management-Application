from sqlalchemy import Column, Date as SQLDate, Float, Index, Integer, String
from app.database import Base


class ExpenseModel(Base):
    __tablename__ = "expenses"

    expense_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    date = Column(SQLDate, nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)

    __table_args__ = (
        Index("idx_expenses_date_category", "date", "category"),
    )