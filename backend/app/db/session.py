from collections.abc import Generator
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()

# A Vercel deployment can create many short-lived function instances. Giving
# every instance SQLAlchemy's default five-connection pool quickly exhausts a
# small Supabase session pool. NullPool keeps each database connection scoped
# to the request/session and returns it as soon as get_db() closes the session.
engine_options: dict = {"pool_pre_ping": True}
if os.getenv("VERCEL"):
    engine_options["poolclass"] = NullPool
    # Supabase transaction pooling does not support session-scoped prepared
    # statements. Psycopg otherwise begins preparing frequently used queries
    # automatically after its default threshold.
    engine_options["connect_args"] = {"prepare_threshold": None}

engine = create_engine(settings.database_url, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
