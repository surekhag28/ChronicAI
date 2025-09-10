import os
import json
import pandas as pd
import logging
from supabase import create_client
from typing import Annotated, List, Dict, Any
from chronic_ai_app.app.state import AppState
from chronic_ai_app.boot import get_supabase

from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage


def get_profile_details(user_id: str) -> Dict[str, Any]:
    """
    Gets profile details for the user
    """

    _SUPABASE = get_supabase()

    detail_rows = (
        _SUPABASE.rpc("profile_details", {"uid": user_id}).execute().data or []
    )
    profile_details = detail_rows[0] or {}

    return profile_details


def get_health_details(user_id: str) -> Dict[str, Any]:
    """
    Gets health indicators for the user
    """
    _SUPABASE = get_supabase()

    health_details = (
        _SUPABASE.rpc("medical_tests_latest", {"uid": user_id}).execute().data or []
    )
    health_indicators = health_details[0] or {}

    return health_indicators


@tool
def get_weekly_metrics(
    user_id: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Fetch weekly metrics via RPC `dashboard_weekly_all_v1(uid text)`.
    Return a pure-JSON ToolMessage {"weekly_metrics": ...} for the LLM to read next turn.
    Also stage raw_metrics in state so it’s committed when the agent node finishes.
    """
    _SUPABASE = get_supabase()

    if _SUPABASE is None:
        raise RuntimeError(
            "Supbase client needs to be initialised.Call init_supabase() on startup"
        )

    response = _SUPABASE.rpc("dashboard_weekly_all_v1", {"uid": user_id}).execute().data

    tm = ToolMessage(
        content=json.dumps({"weekly_metrics": response}), tool_call_id=tool_call_id
    )

    return Command(
        update={
            "messages": state["messages"] + [tm],
        },
    )
