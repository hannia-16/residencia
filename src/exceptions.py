from pydantic import BaseModel, Field


class AppError(Exception):
    status_code = 500
    code = "internal_error"
    message = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.headers = headers
        super().__init__(self.message)


class ErrorDetail(BaseModel):
    code: str = Field(examples=["user_not_found"])
    message: str = Field(examples=["No user matches the given identifier."])


class ErrorResponse(BaseModel):
    detail: ErrorDetail

    @classmethod
    def from_error(cls, error: AppError) -> "ErrorResponse":
        return cls(detail=ErrorDetail(code=error.code, message=error.message))
