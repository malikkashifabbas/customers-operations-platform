"""HTTP routes for chatting with the support agent: one JSON route and one SSE streaming route."""

from django.http import StreamingHttpResponse
from ninja import Router

from . import services
from .auth import CUSTOMER_HEADER, CustomerHeaders
from .schemas import ChatIn, ChatOut

router = Router(tags=["chat"], auth=CustomerHeaders())

# Ninja auth can document only one header, so the customer header is added to the docs by hand.
CUSTOMER_HEADER_DOCS = {
    "parameters": [
        {
            "in": "header",
            "name": CUSTOMER_HEADER,
            "required": True,
            "schema": {"type": "string", "format": "uuid"},
            "description": "public_id of the logged-in customer (temporary until JWT)",
        }
    ]
}


@router.post("/messages", response=ChatOut, openapi_extra=CUSTOMER_HEADER_DOCS)
def send_message(request, payload: ChatIn):
    return services.run_chat(principal=request.auth, message=payload.message, conversation_id=payload.conversation_id)


@router.post("/messages/stream", openapi_extra=CUSTOMER_HEADER_DOCS)
def stream_message(request, payload: ChatIn):
    events = services.stream_chat(principal=request.auth, message=payload.message, conversation_id=payload.conversation_id)
    response = StreamingHttpResponse(events, content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
