import re

_PHONE_NOISE = re.compile(r"[\s\-().]")


def normalize_phone(phone: str) -> str:
    return _PHONE_NOISE.sub("", phone)
