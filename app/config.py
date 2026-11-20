
import os
from pydantic import BaseModel


class Settings(BaseModel):
    PROJECT_NAME: str = "Expense Management Application"
    VERSION: str = "3.0.0"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./expenses.db")
    DEFAULT_SALARY: float = 50000.0


settings = Settings()