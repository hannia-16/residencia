from src.exceptions import AppError


class DatabaseUnavailable(AppError):
    status_code = 503
    code = "database_unavailable"
    message = "The database is not reachable."
