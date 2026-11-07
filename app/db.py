"""Database engine and session dependency; schema setup lives in app.migrate."""

import os
from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@lru_cache(maxsize=4)
def _session_factory(url: str) -> sessionmaker[Session]:
    engine_options = (
        {"connect_args": {"connect_timeout": 3}} if url.startswith("postgresql") else {}
    )
    return sessionmaker(
        bind=create_engine(url, pool_pre_ping=True, **engine_options),
        expire_on_commit=False,
    )


def database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./releaseops.db")


def get_session() -> Generator[Session, None, None]:
    session = _session_factory(database_url())()
    try:
        yield session
    finally:
        session.close()
