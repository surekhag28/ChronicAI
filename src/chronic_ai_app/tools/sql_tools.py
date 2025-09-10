import os
import re
import json
import pandas as pd
import logging
import time

from supabase import create_client
from typing import Annotated, List, Dict, Any
from chronic_ai_app.app.state import AppState
from chronic_ai_app.boot import get_supabase

from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from langchain_community.vectorstores import SupabaseVectorStore
from chronic_ai_app.policy import allowed_tables
from dotenv import load_dotenv

load_dotenv()
_SQL_LOG_FILE = os.path.join(
    os.path.dirname(__file__), os.getenv("SQL_AUDIT_LOG", "logs/sql_audit.log")
)

_SUPABASE = None
_RE_SELECT = re.compile(r"^\s*(SELECT|WITH)\b", re.I)
_RE_BAD = re.compile(r";/\*|/*\|--", re.M)

_RE_FENCE = re.compile(r"^\s*```(?:sql)?\s*|\s*```\s*$", re.I | re.M)
_RE_LEADING_COMMENTS = re.compile(r"^\s*(?:--[^\n]*\n|\s*/\*.*?\*/\s*)*", re.S | re.M)


def _sanitize_sql(s: str) -> str:
    if not s:
        return ""
    s = s.lstrip("\ufeff")  # drop BOM if present
    s = _RE_FENCE.sub("", s)  # strip ```sql fences
    s = _RE_LEADING_COMMENTS.sub("", s)  # drop leading comments
    s = s.strip().rstrip(";").strip()  # trim & drop trailing ';'
    return s


def _log(uid: str, kind: str, **kw):
    try:
        with open(_SQL_LOG_FILE, "a") as f:
            f.write(
                json.dumps({"ts": time.time(), "user_id": uid, "kind": kind, **kw})
                + "\n"
            )
    except Exception as e:
        pass


def _check_allowed_tables(sql: str) -> None:
    lowered = sql.lower()

    refs = [
        m.group(2)
        for m in re.finditer(
            r"\b(from|join)\s+([a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)?)", lowered
        )
    ]
    if not refs:
        return

    allow_tbls = {tbl.lower() for tbl in allowed_tables()}
    if not allow_tbls:
        raise ValueError("Allow tables list is empty; refusing to run query")

    for tbl in refs:
        t = tbl.lower()
        base = t.split(".")[-1]
        if base not in allow_tbls and t not in allow_tbls:
            raise ValueError(
                f"Table {tbl} is not allow-listed by policy. Can't run the query"
            )


def _must_have_user_filter(sql: str) -> None:
    if "user_id" not in sql.lower():
        raise ValueError(
            "Query must include a user_id filter (e.g., WHERE user_id= '<SESSION_UID>')"
        )


def _normalise_rows(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    exec_sql_readonly returns rows like {"to_jsonb": {...}, "to_jsob":{...}, ....}; unwrap to plain dict rows.
    """
    out = []

    for r in data:
        if isinstance(r, dict):
            if "to_jsonb" in r and len(r) == 1:
                val = r["to_jsonb"]
                out.append(val if isinstance(val, dict) else {"value": val})
            elif "row" in r and len(r) == 1:
                val = r["row"]
                out.append(val if isinstance(val, dict) else {"value": val})
            else:
                out.append(r)
        else:
            out.append({"value": r})

    return out


def sql_schema(
    *,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Returns a compact JSON of allow-list tables to help model write correct SQL
    (Queries information_schema via guarded RPC).
    """

    _SUPABASE = get_supabase()

    table_list = sorted(allowed_tables())

    res = _SUPABASE.rpc("schema_snapshot_v1", {"tables": table_list}).execute()
    rows = res.data or []
    tm = ToolMessage(content=json.dumps({"schema": rows}), tool_call_id=tool_call_id)
    return Command(update={"messages": state["messages"] + [tm]})


@tool
def sql_run_readonly(
    sql: str,
    *,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Execute ad-hoc READ-ONLY SQL SELECT/WITH via exec_sql_readonly rpc call.
    Enforces: SELECT/WITH only, no comments/semicolons and DML operations.
    Considers YAML allow-list tables, explicit user_id filter.
    Returns ToolMessage: {"rows":[...], "row_count":N}
    """

    _SUPABASE = get_supabase()

    user_id = state.get("user_id") or ""
    sql = _sanitize_sql(sql)

    if not _RE_SELECT.match(sql):
        raise ValueError("Only SELECT/WITH queries are allowed")

    if _RE_BAD.match(sql):
        raise ValueError("Comments or multiple statements are not allowed")

    _check_allowed_tables(sql)
    _must_have_user_filter(sql)

    t0 = time.time()
    res = _SUPABASE.rpc("exec_sql_readonly_v2", {"query": sql}).execute()
    rows = _normalise_rows(res.data or [])
    ms = round((time.time() - t0) * 1000, 2)
    _log(user_id, "sql_run_readonly", row_count=len(rows), latency_ms=ms)

    payload = {"rows": rows[:200], "row_count": len(rows)}
    tm = ToolMessage(content=json.dumps(payload), tool_call_id=tool_call_id)

    return Command(update={"messages": state["messages"] + [tm]})


@tool
def persist_insight(
    summary: str,
    *,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Persist brief natural-language summary into AppState.chat.last_insights for follow-ups.
    """

    tm = ToolMessage(content="[insight-recorded]", tool_call_id=tool_call_id)

    return Command(
        update={
            "messages": state["messages"] + [tm],
            "chat": {"last_insight": summary},
        },
        graph=Command.PARENT,
    )
