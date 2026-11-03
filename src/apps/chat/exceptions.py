from core.exceptions import DomainError


class AssistantUnavailable(DomainError):
    code = "ASSISTANT_UNAVAILABLE"
    status_code = 503
    message = "The assistant is unavailable right now, please try again in a moment."


class ConversationBusy(DomainError):
    code = "CONVERSATION_BUSY"
    status_code = 409
    message = "The previous message in this conversation is still being answered."


class ConfirmationPending(DomainError):
    code = "CONFIRMATION_PENDING"
    status_code = 409
    message = "Please confirm or cancel the waiting action first, with POST /api/chat/confirm."


class NothingToConfirm(DomainError):
    code = "NOTHING_TO_CONFIRM"
    status_code = 409
    message = "Nothing in this conversation is waiting for confirmation."


class RateLimited(DomainError):
    code = "RATE_LIMITED"
    status_code = 429
    message = "Too many messages, please wait a minute and try again."
