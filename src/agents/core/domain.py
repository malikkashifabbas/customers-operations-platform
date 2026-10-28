"""What every domain specialist must declare so the supervisor can route to it and the orchestrator can run it."""

from collections.abc import Callable
from dataclasses import dataclass

from langgraph.graph.state import CompiledStateGraph


@dataclass(frozen=True)
class DomainSpec:
    name: str
    description: str  # the supervisor reads this to decide which specialist gets the question
    build: Callable[[], CompiledStateGraph]
