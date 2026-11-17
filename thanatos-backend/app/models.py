"""Tablas (SQLite vía SQLAlchemy). Capa 3 del diagrama aprobado:
"Sesiones por ID" y "Frases/Emociones", más alertas y creaciones de ejercicios.

PRIVACIDAD: aquí se guardan TRANSCRIPCIONES y textos que la persona produce.
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
    # Solo tanatólogos: teléfono para los avisos por WhatsApp.
    telefono: Mapped[str | None] = mapped_column(String(30), nullable=True)
    activo: Mapped[bool] = mapped_column(default=True)
    creado_en: Mapped[datetime] = mapped_column(default=_ahora)


class Sesion(Base):
    """Una conversación o un ejercicio. El id (hex) es el `session_id` de la API."""
    __tablename__ = "sesiones"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    # "conversacion" (libre) o el id de un ejercicio (ver services/ejercicios.py).
    tipo: Mapped[str] = mapped_column(String(30), default="conversacion", server_default="conversacion")
    iniciada_en: Mapped[datetime] = mapped_column(default=_ahora)


class Mensaje(Base):
    """Cada frase de la conversación (del usuario o del acompañante)."""
    __tablename__ = "mensajes"

    id: Mapped[int] = mapped_column(primary_key=True)
    sesion_id: Mapped[str] = mapped_column(ForeignKey("sesiones.id"), index=True)
    rol: Mapped[str] = mapped_column(String(10))   # "user" o "assistant" (formato de chat de Ollama)
    texto: Mapped[str] = mapped_column(Text)
    emocion: Mapped[str | None] = mapped_column(String(30), nullable=True)   # sin usar todavía
    riesgo: Mapped[str | None] = mapped_column(String(10), nullable=True)    # verde / amarillo / rojo
    creado_en: Mapped[datetime] = mapped_column(default=_ahora)


class RegistroEmocion(Base):
    """Emoción que la persona elige en "Registrar emoción" (la declara ella misma)."""
    __tablename__ = "registros_emocion"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    emocion: Mapped[str] = mapped_column(String(30))
    intensidad: Mapped[int | None] = mapped_column(nullable=True)   # 1 a 5, opcional
    creado_en: Mapped[datetime] = mapped_column(default=_ahora)


class Creacion(Base):
    """Algo que la persona conserva de un ejercicio: una carta o un relato de legado."""
    __tablename__ = "creaciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    sesion_id: Mapped[str | None] = mapped_column(ForeignKey("sesiones.id"), nullable=True)
    ejercicio: Mapped[str] = mapped_column(String(30))   # cartas_simbolicas | legado_emocional
    titulo: Mapped[str | None] = mapped_column(String(120), nullable=True)
    texto: Mapped[str] = mapped_column(Text)
    riesgo: Mapped[str | None] = mapped_column(String(10), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(default=_ahora)


class Alerta(Base):
    """Aviso para el tanatólogo: riesgo detectado o solicitud de contacto."""
    __tablename__ = "alertas"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)   # el paciente
    tanatologo_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True, index=True)
    sesion_id: Mapped[str | None] = mapped_column(ForeignKey("sesiones.id"), nullable=True)
    origen: Mapped[str] = mapped_column(String(20))    # "riesgo" | "contacto"
    nivel: Mapped[str] = mapped_column(String(10))     # "amarillo" | "rojo" | "contacto"
    motivo: Mapped[str] = mapped_column(String(200))   # categorías, NO la frase de la persona
    estado: Mapped[str] = mapped_column(String(12), default="nueva")   # nueva | vista | atendida
    creado_en: Mapped[datetime] = mapped_column(default=_ahora)
    atendida_en: Mapped[datetime | None] = mapped_column(nullable=True)

class SenalRiesgo(Base):
    """Una señal amarilla o roja detectada en algo que dijo la persona. Una fila por
    detección (sin deduplicar, a diferencia de las alertas). Guarda SOLO categorías,
    nunca la frase: con esto se explica el semáforo sin mostrar la conversación."""
    __tablename__ = "senales_riesgo"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    sesion_id: Mapped[str | None] = mapped_column(ForeignKey("sesiones.id"), nullable=True)
    fuente: Mapped[str] = mapped_column(String(15))        # conversacion | dictado | creacion
    nivel: Mapped[str] = mapped_column(String(10))         # amarillo | rojo
    categorias: Mapped[str] = mapped_column(String(200))   # "aislamiento, desesperanza"
    reglas_version: Mapped[str] = mapped_column(String(10))
    creado_en: Mapped[datetime] = mapped_column(default=_ahora)


class ResumenPaciente(Base):
    """Último resumen automático de lo que el paciente habló, para el tanatólogo."""
    __tablename__ = "resumenes_paciente"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    desde: Mapped[datetime] = mapped_column()
    hasta: Mapped[datetime] = mapped_column()
    num_mensajes: Mapped[int] = mapped_column()
    texto: Mapped[str] = mapped_column(Text)
    generado_en: Mapped[datetime] = mapped_column(default=_ahora)

class EjercicioMostrado(Base):
    """Ejercicio de desahogo que se le explicó a la persona: sirve para no repetir el mismo
    dos veces seguidas y para el dashboard."""
    __tablename__ = "ejercicios_mostrados"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    ejercicio: Mapped[str] = mapped_column(String(30))
    creado_en: Mapped[datetime] = mapped_column(default=_ahora)