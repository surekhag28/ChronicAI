import os
from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from chronic_ai_app.tools.sql_tools import sql_schema, sql_run_readonly, persist_insight
from chronic_ai_app.tools.handoff import handoff_to
from chronic_ai_app.tools.record_assessment import record_assessment
from chronic_ai_app.prompts.analytics_prompt import ANALYTICS_PROMPT
from chronic_ai_app.app.state import AppState


def build_analytics_agent():

    return create_react_agent(
        model=str(os.getenv("MODEL")),
        tools=[handoff_to, sql_schema, sql_run_readonly, persist_insight],
        name="analytics_agent",
        prompt=ANALYTICS_PROMPT,
    )
