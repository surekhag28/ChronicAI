import json
from langchain_core.messages import SystemMessage
from chronic_ai_app.app.state import AppState
from typing import Dict


def inject_profile_context(state: AppState) -> dict:

    profile = state.get("profile") or {}
    payload = {"assessment": profile.get("assessment"), "trends": profile.get("trends")}
    msgs = list(state.get("messages", []))
    msgs.append(SystemMessage(content="PROFILE_CONTENT_JSON\n" + json.dumps(payload)))
    return {"messages": msgs}
