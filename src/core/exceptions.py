"""Domain errors carry a stable code and HTTP status so every API answers errors the same way."""


class DomainError(Exception):
    code = "DOMAIN_ERROR"
    status_code = 400
    message = "Something went wrong."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message
