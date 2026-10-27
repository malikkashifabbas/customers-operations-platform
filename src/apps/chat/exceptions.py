from core.exceptions import DomainError


class AssistantUnavailable(DomainError):
    code = "ASSISTANT_UNAVAILABLE"
    status_code = 503
    message = "The assistant is unavailable right now, please try again in a moment."


class ConversationBusy(DomainError):
    code = "CONVERSATION_BUSY"
    status_code = 409
    message = "The previous message in this conversation is still being answered."


class RateLimited(DomainError):
    code = "RATE_LIMITED"
    status_code = 429
    message = "Too many messages, please wait a minute and try again."
