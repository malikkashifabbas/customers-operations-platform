from core.exceptions import DomainError


class TicketBusy(DomainError):
    code = "TICKET_BUSY"
    status_code = 409
    message = "The assistant is still answering this ticket. Wait for the reply, then write again."


class TicketWaitingApproval(DomainError):
    code = "TICKET_WAITING_APPROVAL"
    status_code = 409
    message = "A staff member is deciding on this ticket. You can write again after their decision."


class FollowUpLimitReached(DomainError):
    code = "FOLLOW_UP_LIMIT_REACHED"
    status_code = 409
    message = "This ticket has reached its message limit. Please open a new ticket."


class TicketRateLimited(DomainError):
    code = "RATE_LIMITED"
    status_code = 429
    message = "Too many messages. Please wait a minute."


class ApprovalNotPending(DomainError):
    code = "APPROVAL_NOT_PENDING"
    status_code = 409
    message = "This ticket is not waiting for a staff decision (already decided, or nothing to approve)."
