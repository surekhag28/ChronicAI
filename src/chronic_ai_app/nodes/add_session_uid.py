from langchain_core.messages import SystemMessage
from chronic_ai_app.app.state import AppState
from typing import Dict


def add_session_uid(state: AppState) -> dict:

    msgs = list(state.get("messages", []))
    msgs.append(SystemMessage(content=f"SESSION_UID={state['user_id']}"))
    return {"messages": msgs}
