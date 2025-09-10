import os
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from chronic_ai_app.tools.weekly_metrics import get_weekly_metrics
from chronic_ai_app.tools.record_assessment import record_assessment
from chronic_ai_app.prompts.profile_prompt import PROFILE_PROMPT
from chronic_ai_app.app.state import AppState

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

llm = ChatOpenAI(
    model=os.getenv("MODEL", "gpt-4o-mini"),
    temperature=0,
    streaming=True,
)


def build_profile():
    return create_react_agent(
        model=llm,  # str(os.getenv("MODEL")),
        tools=[get_weekly_metrics, record_assessment],
        name="profile_agent",
        prompt=PROFILE_PROMPT,
    )
