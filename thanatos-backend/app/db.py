"""Conexión a SQLite con SQLAlchemy.

Se usa SQLAlchemy (y no sqlite3 a mano) porque así, si algún día se migra a
Postgres, solo cambia DATABASE_URL. SQLite sigue siendo lo aprobado.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# check_same_thread=False: FastAPI atiende peticiones desde varios hilos y
# SQLite, por defecto, no permite compartir la conexión entre hilos.
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def _configurar_sqlite(conexion, _registro):
    """Se ejecuta en cada conexión nueva."""
    cursor = conexion.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")   # SQLite NO valida llaves foráneas si no se pide
    cursor.execute("PRAGMA journal_mode=WAL")  # permite leer mientras se escribe
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Clase base de todas las tablas."""


def get_db():
    """Dependencia de FastAPI: una sesión de BD por petición, cerrada al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()