import os
import json
import pandas as pd
import logging
from supabase import create_client
from typing import Annotated, List, Dict, Any
from chronic_ai_app.app.state import AppState
from chronic_ai_app.boot import get_vectorstore

from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from langchain_community.vectorstores import SupabaseVectorStore


def _snippets(docs: List[Any]):
    content: List[str] = []

    for doc in docs:
        text = getattr(doc, "page_content", "") or ""
        content.append(text[:800])

    return content


@tool
def rag_retrieve(
    section: str,
    query: str,
    k: int = 3,
    *,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Retrive upto k documents from Supabase vectorstore for the given query.
    Returns a ToolMessage with **pure JSON**:
        {"snippets": ["...","...","..."]}
    """
    _VECTORSTORE = get_vectorstore()

    try:
        if _VECTORSTORE is None:
            raise RuntimeError(
                "Retriever not initialised. Call init_supabase_vectorestore."
            )

        docs = _VECTORSTORE.similarity_search(query, k=3)
        payload = {"snippets": _snippets(docs)}
    except Exception as e:
        payload = {"error": f"{type(e).__name__}: {e}"}

    tm = ToolMessage(content=json.dumps(payload), tool_call_id=tool_call_id)

    return Command(update={"messages": state["messages"] + [tm]})
