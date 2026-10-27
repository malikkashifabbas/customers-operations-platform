"""Every Redis key pattern lives here, all under the 'opspilot:' prefix so they are easy to find and clean."""

PREFIX = "opspilot"


def event_done(event_id: str) -> str:
    return f"{PREFIX}:evt:done:{event_id}"


def ticket_events(ticket_public_id: str) -> str:
    return f"{PREFIX}:ticket:{ticket_public_id}:events"


def lock(name: str) -> str:
    return f"{PREFIX}:lock:{name}"


def rate(scope: str, subject: str, window: int) -> str:
    return f"{PREFIX}:rate:{scope}:{subject}:{window}"
