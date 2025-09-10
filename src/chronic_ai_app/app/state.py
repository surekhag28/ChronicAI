from typing import TypedDict, Annotated, List, Dict, Any, Required
from langgraph.graph import add_messages
from langchain_core.messages import AnyMessage
from langgraph.prebuilt.chat_agent_executor import AgentState
from chronic_ai_app.app.reducers import deep_merge


class ProfileState(TypedDict):
    profile_details: Dict[str, Any]
    health_indicators: Dict[str, Any]
    raw_metrics: Dict[str, Any]
    assessment: Dict[str, Any]
    trends: Dict[str, Any]
    recommendations: Dict[str, Any]


class ChatState(TypedDict):
    last_insight: str


class AppState(TypedDict, total=False):
    user_id: str
    messages: Annotated[List[AnyMessage], add_messages]
    profile: Annotated[ProfileState, deep_merge]
    chat: Annotated[ChatState, deep_merge]
