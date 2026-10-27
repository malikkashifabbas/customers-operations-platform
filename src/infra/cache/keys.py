"""Every Redis key pattern lives here, all under the 'opspilot:' prefix so they are easy to find and clean."""

PREFIX = "opspilot"


def event_done(event_id: str) -> str:
    return f"{PREFIX}:evt:done:{event_id}"
