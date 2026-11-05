"""Tablas. Corresponden a la capa 3 del diagrama aprobado:
"Sesiones por ID" y "Frases/Emociones".

PRIVACIDAD: aquí se guardan TRANSCRIPCIONES de conversaciones sobre duelo.
No se guarda el audio del usuario. El archivo .db nunca debe subirse a Git.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Rol(str, enum.Enum):
    ADULTO_MAYOR = "adulto_mayor"
    TANATOLOGO = "tanatologo"


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    usuario: Mapped[str] = mapped_column(String(60), unique=True, index=True)  # siempre en minúsculas
    password_hash: Mapped[str] = mapped_column(String(200))  # NUNCA la contraseña en claro
    rol: Mapped[str] = mapped_column(String(20))             # valores de Rol
    # Solo para adultos mayores: qué tanatólogo los supervisa (alimenta el dashboard).
    tanatologo_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    activo: Mapped[bool] = mapped_column(default=True)
    creado_en: Mapped[datetime] = mapped_column(default=_ahora)


class Sesion(Base):
    """Una conversación completa. El id (hex) es el `session_id` de la API."""
    __tablename__ = "sesiones"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    iniciada_en: Mapped[datetime] = mapped_column(default=_ahora)


class Mensaje(Base):
    """Cada frase de la conversación (del usuario o del acompañante)."""
    __tablename__ = "mensajes"

    id: Mapped[int] = mapped_column(primary_key=True)
    sesion_id: Mapped[str] = mapped_column(ForeignKey("sesiones.id"), index=True)
    rol: Mapped[str] = mapped_column(String(10))   # "user" o "assistant" (formato de chat de Ollama)
    texto: Mapped[str] = mapped_column(Text)
    # Se llenarán en la etapa de riesgo (RN-08). Por ahora quedan vacíos.
    emocion: Mapped[str | None] = mapped_column(String(30), nullable=True)
    riesgo: Mapped[str | None] = mapped_column(String(10), nullable=True)  # verde / amarillo / rojo
    creado_en: Mapped[datetime] = mapped_column(default=_ahora)