from core.exceptions import DomainError


class InvalidCredentials(DomainError):
    code = "INVALID_CREDENTIALS"
    status_code = 401
    message = "These login details are not correct."


class LoginLocked(DomainError):
    code = "LOGIN_LOCKED"
    status_code = 429
    message = "Too many failed login attempts, please try again later."


class WeakPassword(DomainError):
    code = "WEAK_PASSWORD"
    status_code = 400
    message = "This password is too weak."


class UnknownTenant(DomainError):
    code = "UNKNOWN_TENANT"
    status_code = 404
    message = "This company was not found."


class InvalidToken(DomainError):
    code = "INVALID_TOKEN"
    status_code = 401
    message = "This token is not valid, please log in again."
