class AppException(Exception):
    """Base exception class for domain level errors."""
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ExpenseNotFoundError(AppException):
    def __init__(self, expense_id: int):
        super().__init__(
            code="EXPENSE_NOT_FOUND",
            message=f"Expense with id {expense_id} was not found.",
            status_code=404,
        )


class ConcurrencyConflictError(AppException):
    def __init__(self, message: str = "This expense was modified by another client. Please fetch the latest version and retry."):
        super().__init__(
            code="CONCURRENCY_CONFLICT",
            message=message,
            status_code=409,
        )