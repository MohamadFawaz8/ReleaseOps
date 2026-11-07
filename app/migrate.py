"""One-shot initial schema initializer. Normal service startup never mutates schema."""

from sqlalchemy import create_engine

from app.db import database_url
from app.models import Base


def main() -> None:
    engine = create_engine(database_url(), pool_pre_ping=True)
    Base.metadata.create_all(engine)
    print("ReleaseOps schema initialized (initial version).")


if __name__ == "__main__":
    main()
