# server.py (snippet)

import os, uuid, threading
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from chronic_ai_app.app.state import AppState, ProfileState
from chronic_ai_app.policy import configure_policy
from chronic_ai_app.main import build_profile_flow, build_chat_flow
from chronic_ai_app.boot import init_supabase, init_supabase_vectorstore
from chronic_ai_app.ingestion.embeddings import get_embedding_model
from chronic_ai_app.tools.weekly_metrics import get_profile_details, get_health_details
from fastapi.responses import StreamingResponse


# ---------- globals ----------
_INITIALIZED = False
_INIT_LOCK = threading.RLock()
PROFILE_FLOW = None
CHAT_FLOW = None
SESSIONS: Dict[str, AppState] = {}
SESS_LOCK = threading.RLock()


def make_profile_state() -> ProfileState:
    return {
        "profile_details": {},
        "health_indicators": {},
        "raw_metrics": {},
        "assessment": {},
        "trends": {},
        "recommendations": {},
    }


def make_app_state(user_id: str) -> AppState:
    return {
        "user_id": user_id,
        "messages": [],
        "profile": make_profile_state(),
        "chat": {"last_insight": ""},
    }


def _log(msg: str) -> None:
    print(f"[init] {msg}", flush=True)


def _init_once() -> None:
    """Initialize exactly once per process. Sets globals only after success."""
    global _INITIALIZED, PROFILE_FLOW, CHAT_FLOW
    if _INITIALIZED:
        return
    _log("starting init")

    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
    ).strip()
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_*KEY missing")
    sb = init_supabase(url, key)
    _log("supabase ok")

    # 2) Vector store
    embeddings = get_embedding_model()
    init_supabase_vectorstore(
        embeddings=embeddings,
        table_name=os.getenv("SB_VECTOR_TABLE", "documents"),
        query_name=os.getenv("SB_VECTOR_FN", "match_documents"),
    )
    _log("vectorstore ok")

    configure_policy(str(os.getenv("ALLOWED_TABLES_YML_FILE")), 300)

    pf = build_profile_flow()
    if pf is None:
        raise RuntimeError("build_profile_flow() returned None")
    cf = build_chat_flow()
    if cf is None:
        raise RuntimeError("build_chat_flow() returned None")

    PROFILE_FLOW = pf
    CHAT_FLOW = cf
    _INITIALIZED = True
    _log(f"ready profile_flow={id(PROFILE_FLOW)} chat_flow={id(CHAT_FLOW)}")


def ensure_ready() -> None:
    """Thread-safe lazy init on first request."""
    if _INITIALIZED and (PROFILE_FLOW is not None) and (CHAT_FLOW is not None):
        return
    with _INIT_LOCK:
        if not _INITIALIZED or PROFILE_FLOW is None or CHAT_FLOW is None:
            _init_once()


# ---------- app ----------
app = FastAPI(title="ChronicAI Backend")


DEV_LOVABLE = (
    os.getenv("LOVABLE_ORIGIN") or "https://preview--wellness-guide-ui.lovable.app"
).strip()
NGROK_HOST = (os.getenv("NGROK_HOST") or "").strip()
allow_origins = [DEV_LOVABLE] + ([NGROK_HOST] if NGROK_HOST else [])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins or ["*"],
    allow_origin_regex=r"^https://([a-z0-9-]+\.)*(lovable\.app|lovable\.dev|ngrok\.app|ngrok-free\.app|loca\.lt)$",
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
    max_age=600,
)

_init_once()


# health
@app.get("/health")
def health():
    return {
        "initialized": _INITIALIZED,
        "profile_flow": bool(PROFILE_FLOW),
        "chat_flow": bool(CHAT_FLOW),
        "profile_flow_id": id(PROFILE_FLOW) if PROFILE_FLOW else None,
        "chat_flow_id": id(CHAT_FLOW) if CHAT_FLOW else None,
    }


# profile refresh
class ProfileRefreshIn(BaseModel):
    session_id: Optional[str] = None
    user_id: str


class ProfileOut(BaseModel):
    session_id: str
    profile_details: Dict[str, Any] = {}
    health_indicators: Dict[str, Any] = {}
    raw_metrics: Dict[str, Any] = {}
    assessment: Dict[str, Any] = {}
    trends: Dict[str, Any] = {}
    recommendations: Dict[str, Any] = {}


@app.post("/profile/refresh", response_model=ProfileOut)
def profile_refresh(in_: ProfileRefreshIn, request: Request):
    assert PROFILE_FLOW is not None

    sid = in_.session_id or uuid.uuid4().hex
    with SESS_LOCK:
        state = SESSIONS.get(sid) or make_app_state(in_.user_id)
        state["user_id"] = in_.user_id
        SESSIONS[sid] = state

    try:
        details = get_profile_details(in_.user_id) or {}
        indicators = get_health_details(in_.user_id) or {}
    except Exception as e:
        _log(f"prefetch warn: {e}")

    new_state = PROFILE_FLOW.invoke(state)

    with SESS_LOCK:
        SESSIONS[sid] = new_state

    prof = new_state.get("profile")

    # print(prof)

    return ProfileOut(
        session_id=sid,
        profile_details=details,
        health_indicators=indicators,
        raw_metrics=prof.get("raw_metrics", {}),
        assessment=prof.get("assessment", {}),
        trends=prof.get("trends", {}),
        recommendations=prof.get("recommendations", {}),
    )


# chat
class ChatIn(BaseModel):
    session_id: Optional[str] = None
    user_id: str
    message: str


class ChatOut(BaseModel):
    session_id: str
    assistant: str
    last_insight: Optional[str] = None
    recommendations: Optional[Dict[str, str]] = None


@app.post("/chat", response_model=ChatOut)
def chat(in_: ChatIn, request: Request):
    assert CHAT_FLOW is not None  # ensure initialized

    sid = in_.session_id or uuid.uuid4().hex
    with SESS_LOCK:
        state = SESSIONS.get(sid) or make_app_state(in_.user_id)
        state["user_id"] = in_.user_id
        state["messages"].append(HumanMessage(content=in_.message))
        SESSIONS[sid] = state

    for step in CHAT_FLOW.stream(state, config={"recursion_limit": 10}):
        print(step)

    new_state = CHAT_FLOW.invoke(state)

    with SESS_LOCK:
        SESSIONS[sid] = new_state

    msgs = new_state.get("messages") or []
    assistant_text = getattr(msgs[-1], "content", "") if msgs else ""
    last_insight = new_state.get("chat", {}).get("last_insight")
    recs = new_state.get("profile", {}).get("recommendations") or None

    return ChatOut(
        session_id=sid,
        assistant=assistant_text,
        last_insight=last_insight,
        recommendations=recs,
    )
