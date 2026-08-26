from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import DATABASE_URL, STORAGE_DIR

STORAGE_DIR.mkdir(parents=True, exist_ok=True)

_is_sqlite = DATABASE_URL.startswith("sqlite")
_connect_args = {"check_same_thread": False} if _is_sqlite else {}
# NullPool para SQLite: cada sesión abre y cierra su propia conexión en vez
# de mantenerla en un pool, evitando que el archivo .db quede bloqueado en
# Windows (relevante para demo.py, que borra app/storage/ antes de correr).
engine = create_engine(DATABASE_URL, connect_args=_connect_args, poolclass=NullPool if _is_sqlite else None)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from app import models  # noqa: F401 (registra los modelos en Base.metadata)
    Base.metadata.create_all(bind=engine)
