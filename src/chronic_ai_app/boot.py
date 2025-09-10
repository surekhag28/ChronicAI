import os
from dotenv import load_dotenv
from typing import Optional
from supabase import create_client, Client
from chronic_ai_app.policy import configure_policy
from chronic_ai_app.ingestion.embeddings import get_embedding_model
from langchain_community.vectorstores import SupabaseVectorStore


_SB: Optional[Client] = None


def init_supabase(url: str, key: str) -> Client:
    """Call once on startup (e.g., FastAPI lifespan)."""
    global _SB
    _SB = create_client(url, key)
    return _SB


def get_supabase() -> Client:
    """Access from anywhere (agents, tools, nodes)."""
    if _SB is None:
        raise RuntimeError(
            "Supabase not initialized. Call init_supabase(...) at startup."
        )
    return _SB


def init_supabase_vectorstore(
    embeddings,
    table_name: str = "documents",
    query_name: str = "match_documents",
) -> None:
    """
    Initialises a Supabase pgvector-backed vectore store.
    """
    global _VECTORSTORE

    _VECTORSTORE = SupabaseVectorStore(
        client=_SB,
        embedding=embeddings,
        table_name=table_name,
        query_name=query_name,
    )


def get_vectorstore():
    """Access from anywhere (agents, tools, nodes)."""
    if _VECTORSTORE is None:
        raise RuntimeError(
            "Vector store not initialized. Call init_supabase_vectorstore(...) at startup."
        )
    return _VECTORSTORE


""" def boot_supabase():

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    init_supabase(sb)

    embedding_model = get_embedding_model()

    init_supabase_vectorstore(
        sb,
        embeddings=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        table_name=os.getenv("SB_VECTOR_TABLE", "documents"),
        query_name=os.getenv("SB_VECTOR_FN", "match_documents"),
    )

    configure_policy(str(os.getenv("ALLOWED_TABLES_YML_FILE")), 300)

    return sb
 """
