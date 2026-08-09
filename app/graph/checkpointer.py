"""Checkpointer factory for state graph persistence and checkpoint recovery."""

from typing import Optional
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from app.config import settings


def get_checkpointer(use_postgres: bool = False) -> BaseCheckpointSaver:
    """Return configured checkpointer instance for state persistence.
    
    Uses Postgres checkpointer if postgres is available/requested, else MemorySaver for test/in-memory mode.
    """
    if use_postgres:
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            import psycopg
            # Postgres connection checkpointer
            return AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL)
        except Exception:
            # Fallback to MemorySaver if postgres DB connection not active in test environment
            return MemorySaver()
    return MemorySaver()
