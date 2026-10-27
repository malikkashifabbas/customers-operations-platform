from core.exceptions import DomainError


class ApprovalNotPending(DomainError):
    code = "APPROVAL_NOT_PENDING"
    status_code = 409
    message = "This ticket is not waiting for a staff decision (already decided, or nothing to approve)."
