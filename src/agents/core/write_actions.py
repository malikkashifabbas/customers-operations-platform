"""What every tool that changes data needs: run at most once per tool call, and leave an audit row with its result."""

from langchain.tools import ToolRuntime

from apps.agent_actions.models import AgentAction, AgentActionStatus
from apps.agent_actions.services import record_action


def _thread_id(runtime: ToolRuntime) -> str:
    return runtime.config.get("configurable", {}).get("thread_id", "")


def earlier_result(runtime: ToolRuntime) -> str | None:
    """The first run's result: resuming one interrupt reruns every tool call in that reply, and none may act twice."""
    action = AgentAction.objects.filter(thread_id=_thread_id(runtime), tool_call_id=runtime.tool_call_id).first()
    return action.details.get("result") if action else None


def finish(runtime: ToolRuntime, *, action: str, status: AgentActionStatus, details: dict, result: str, target_public_id=None) -> str:
    record_action(
        tenant=runtime.context.tenant,
        customer=runtime.context.customer,
        action=action,
        status=status,
        details={**details, "result": result},
        thread_id=_thread_id(runtime),
        tool_call_id=runtime.tool_call_id,
        target_public_id=target_public_id,
    )
    return result
