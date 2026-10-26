from core.exceptions import DomainError


class AssistantUnavailable(DomainError):
    code = "ASSISTANT_UNAVAILABLE"
    status_code = 503
    message = "The assistant is unavailable right now, please try again in a moment."
