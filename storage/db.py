import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

import logging

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set.")

# Ensure parent dir exists for sqlite file
if DATABASE_URL.startswith("sqlite:///"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args=(
        {"check_same_thread": False} if DATABASE_URL.startswith("sqlite:///") else {}
    ),
)
SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False)
)
Base = declarative_base()


def get_session():
    return SessionLocal()


def _ensure_meta_column():
    """Ensure the `meta` column exists on the `conversations` table. Performs an
    ALTER TABLE when necessary for supported dialects (sqlite, postgresql).
    """
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "conversations" not in insp.get_table_names():
        return
    cols = [c["name"] for c in insp.get_columns("conversations")]
    if "meta" in cols:
        return
    dialect = engine.dialect.name
    with engine.connect() as conn:
        try:
            if dialect == "sqlite":
                conn.execute(text("ALTER TABLE conversations ADD COLUMN meta JSON"))
            elif dialect in ("postgresql", "postgres"):
                conn.execute(text("ALTER TABLE conversations ADD COLUMN meta JSONB"))
            else:
                # best effort for other DBs
                conn.execute(text("ALTER TABLE conversations ADD COLUMN meta JSON"))
        except Exception:
            # If it fails, don't stop the app; the script alternative exists
            logger.exception("Failed to ensure meta column on conversations table")


def init_db():
    # Import models to ensure they are registered with Base.metadata
    try:
        import storage.models  # noqa: F401
    except Exception:
        logger.exception("Failed to import storage.models during init_db")
    Base.metadata.create_all(bind=engine)
    # Try to add new columns (non-destructive) when possible
    _ensure_meta_column()

    # Log engine URL for debugging (useful to verify which DB the running process uses)
    try:
        import os

        url = getattr(engine, "url", None)
        # write to a debug file to make it available across processes
        os.makedirs("logs", exist_ok=True)
        with open("logs/db_engine.log", "a", encoding="utf-8") as fh:
            fh.write(f"init_db called - engine.url={url}\n")
    except Exception:
        logger.exception("Failed to log engine url during init_db")
