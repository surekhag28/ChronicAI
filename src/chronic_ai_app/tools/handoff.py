import json
from typing import Literal, Annotated, Optional
from chronic_ai_app.app.state import AppState

from langgraph.prebuilt import InjectedState
from langchain_core.tools import InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.types import Command


def handoff_to(
    target: Literal["analytics_agent", "recommendation_agent"],
    reason: Optional[str] = None,
    *,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Handoff control to another agent in the same graph.

    Args:
        target: "analytics_agent" or "recommendation_agent"
        reason: short note for logging/audit purposes.

    Effect:
        - Appends a ToolMessage describing handoff
        - Returns Command(goto=target) so the graph jumps to that node/target node
    """

    tm = ToolMessage(
        content=json.dumps({"handoff": target, "reason": reason or ""}),
        tool_call_id=tool_call_id,
    )
    return Command(
        update={"messages": state["messages"] + [tm]}, goto=target, graph=Command.PARENT
    )
