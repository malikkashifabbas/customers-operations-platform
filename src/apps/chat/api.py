"""HTTP routes for chatting with the support agent: one JSON route and one SSE streaming route."""

from django.http import StreamingHttpResponse
from ninja import Router

from apps.accounts.auth import CustomerJWT

from . import services
from .schemas import ChatIn, ChatOut, ConfirmIn

router = Router(tags=["chat"], auth=CustomerJWT())


@router.post("/messages", response=ChatOut)
def send_message(request, payload: ChatIn):
    return services.run_chat(principal=request.auth, message=payload.message, conversation_id=payload.conversation_id)


@router.post("/confirm", response=ChatOut)
def confirm(request, payload: ConfirmIn):
    return services.confirm_chat(principal=request.auth, conversation_id=payload.conversation_id, approved=payload.approved)


@router.post("/messages/stream")
def stream_message(request, payload: ChatIn):
    events = services.stream_chat(principal=request.auth, message=payload.message, conversation_id=payload.conversation_id)
    response = StreamingHttpResponse(events, content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
