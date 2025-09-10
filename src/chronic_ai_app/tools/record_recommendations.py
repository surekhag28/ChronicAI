import os
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
def record_recommendations(
    recs: Dict[str, str],  # {"diets": "summary....", "exercise":"summary...."}
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Persist simple per-section recommendation summary into state.profile.recommendations

    """

    tm = ToolMessage(content="[recommendations-recorded]", tool_call_id=tool_call_id)
    return Command(
        update={
            "messages": state["messages"] + [tm],
            "profile": {
                "recommendations": recs,
            },
        },
        graph=Command.PARENT,
    )
