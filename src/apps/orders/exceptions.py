from core.exceptions import DomainError


class OrderAlreadyExists(DomainError):
    code = "ORDER_ALREADY_EXISTS"
    status_code = 409
    message = "An order with this number already exists."


class CustomerTenantMismatch(DomainError):
    code = "CUSTOMER_TENANT_MISMATCH"
    status_code = 400
    message = "The customer does not belong to this tenant."


class OrderNotCancellable(DomainError):
    code = "ORDER_NOT_CANCELLABLE"
    status_code = 409
    message = "Only pending orders can be cancelled."


class OrderNotRefundable(DomainError):
    code = "ORDER_NOT_REFUNDABLE"
    status_code = 409
    message = "Only paid orders can be refunded."
