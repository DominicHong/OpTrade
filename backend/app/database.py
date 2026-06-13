from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False},  # SQLite-specific
)


def create_db_and_tables() -> None:
    """Create all tables defined by SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a database session per request."""
    with Session(engine) as session:
        yield session
