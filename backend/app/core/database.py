from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings
from app.core.redis_cache import cache_enabled
from app.services.cache_invalidation_hooks import invalidate_caches_for_session


class Base(DeclarativeBase):
    pass


def _engine_kwargs() -> dict:
    url = settings.database_url
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
    }


engine = create_engine(settings.database_url, future=True, **_engine_kwargs())
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@event.listens_for(Session, "before_commit")
def _invalidate_redis_cache_on_write(session: Session) -> None:
    """Drop list/dashboard caches when any ORM change is committed."""
    if not cache_enabled():
        return
    if session.info.get("defer_cache_invalidation") or session.info.get("skip_cache_invalidation"):
        return
    if session.new or session.dirty or session.deleted:
        invalidate_caches_for_session(session)
