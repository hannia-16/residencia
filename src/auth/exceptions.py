from src.exceptions import AppError


class AuthError(AppError):
    status_code = 401
    code = "auth_error"
    message = "Authentication failed."


class InvalidCredentials(AuthError):
    code = "invalid_credentials"
    message = "Incorrect email or password."


class InvalidToken(AuthError):
    code = "invalid_token"
    message = "The provided token is missing, malformed, or expired."


class UserAlreadyExists(AuthError):
    status_code = 409
    code = "user_already_exists"
    message = "A user with that email or username already exists."


class UserNotFound(AuthError):
    status_code = 404
    code = "user_not_found"
    message = "No user matches the given identifier."


class UserNotActive(AuthError):
    status_code = 403
    code = "user_not_active"
    message = "This account is deactivated."
