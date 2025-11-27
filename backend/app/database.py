from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
import os
import time
import logging

# Set up query logger
query_logger = logging.getLogger("sqlalchemy.query_timing")
query_logger.setLevel(logging.DEBUG if os.getenv("DEBUG_QUERIES") else logging.WARNING)

# Slow query threshold in milliseconds
SLOW_QUERY_THRESHOLD_MS = int(os.getenv("SLOW_QUERY_THRESHOLD_MS", "100"))

# Database URL - will use SQLite for local development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shelfsense.db")

# Railway uses postgres:// but SQLAlchemy requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Determine connection args based on database type
is_sqlite = "sqlite" in DATABASE_URL
if is_sqlite:
    connect_args = {"check_same_thread": False}
else:
    # PostgreSQL connection pool settings for production
    connect_args = {}

# Engine configuration based on database type
if is_sqlite:
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True,
    )
else:
    # PostgreSQL with production-ready pool settings
    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True,      # Detect stale connections
        pool_recycle=1800,       # Recycle connections after 30 minutes
        pool_size=5,             # Base pool connections
        max_overflow=10,         # Additional connections under load
        pool_timeout=30,         # Wait for connection timeout
    )


# Query timing event listeners for slow query logging
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Record query start time."""
    conn.info.setdefault("query_start_time", []).append(time.perf_counter())


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log slow queries."""
    start_times = conn.info.get("query_start_time", [])
    if start_times:
        total_time_ms = (time.perf_counter() - start_times.pop()) * 1000

        if total_time_ms > SLOW_QUERY_THRESHOLD_MS:
            # Truncate long queries for logging
            truncated_statement = statement[:500] + "..." if len(statement) > 500 else statement
            truncated_params = str(parameters)[:200] + "..." if len(str(parameters)) > 200 else str(parameters)

            query_logger.warning(
                f"SLOW QUERY ({total_time_ms:.2f}ms): {truncated_statement} | params={truncated_params}"
            )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
