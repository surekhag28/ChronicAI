import os
from langgraph.prebuilt import create_react_agent
from chronic_ai_app.tools.rag_retrieve import rag_retrieve
from chronic_ai_app.tools.record_recommendations import record_recommendations
from chronic_ai_app.tools.sql_tools import persist_insight
from chronic_ai_app.tools.handoff import handoff_to
from chronic_ai_app.prompts.recommendation_prompt import RECS_PROMPT


def build_recommendation():
    return create_react_agent(
        model=str(os.getenv("MODEL")),
        tools=[handoff_to, rag_retrieve, record_recommendations, persist_insight],
        name="recommendation_agent",
        prompt=RECS_PROMPT,
    )
