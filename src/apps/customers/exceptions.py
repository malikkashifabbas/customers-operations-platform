from core.exceptions import DomainError


class CustomerAlreadyExists(DomainError):
    code = "CUSTOMER_ALREADY_EXISTS"
    status_code = 409
    message = "A customer with this phone already exists."
