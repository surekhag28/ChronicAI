import os
import json
import pandas as pd
import logging
from supabase import create_client
from typing import Annotated, List, Dict, Any
from chronic_ai_app.app.state import AppState

from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage


@tool
def record_assessment(
    raw_metrics: Dict[str, Any],
    assessment: Dict[str, Any],
    trends: Dict[str, Any],
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Persist the Profile Agent's results into the graph state.

    Args:
        raw_metrics: weekly metrics JSON
        assessment: Per-section snapshot JSON (summary)
        trends: Per-section natural-language summaries of week-over-week progress.
    Side effects:
        - Writes state.profile.raw_metrics = raw_metrics
        - Writes state.profile.assessment = assessment
        - Writes state.profile.trends = trends
        - Appends a small ToolMessage for traceability

    Returns:
        Command(update=....) to merge these fields into the current AppState.
    """

    tm = ToolMessage(
        content="[assessment-trend] to be saved" + json.dumps(assessment),
        tool_call_id=tool_call_id,
    )

    return Command(
        update={
            "messages": state["messages"] + [tm],
            "profile": {
                "raw_metrics": raw_metrics,
                "assessment": assessment,
                "trends": trends,
            },
        },
        graph=Command.PARENT,
    )
