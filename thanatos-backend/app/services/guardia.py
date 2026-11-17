"""
Revisión de riesgo de CUALQUIER texto que la persona produce (conversación,
dictado de cartas, cartas guardadas). Un solo lugar para que todas las rutas
traten el riesgo igual: clasifica, registra la señal, crea la alerta si hace
falta y, si es ROJO, prepara el mensaje fijo y su audio.

Además aplica "cautela de seguimiento": si en los últimos mensajes de la sesión
hubo una señal amarilla o roja, un mensaje que ya no trae señales NO se trata
como si nada hubiera pasado (el modelo sigue respondiendo con cuidado).
"""
import asyncio
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Mensaje, SenalRiesgo, Usuario
from app.services import alertas, audios_fijos, riesgo

logger = logging.getLogger("thanatos.guardia")

_VENTANA_SEGUIMIENTO = 6   # cuántos mensajes recientes de la persona se revisan


def _hubo_senal_reciente(db: Session, sesion_id: str | None) -> bool:
    """True si entre los últimos mensajes de la persona en esta sesión hubo amarillo o rojo."""
    if not sesion_id:
        return False
    previos = db.scalars(
        select(Mensaje.riesgo)
        .where(Mensaje.sesion_id == sesion_id, Mensaje.rol == "user")
        .order_by(Mensaje.id.desc())
        .limit(_VENTANA_SEGUIMIENTO)
    ).all()
    return any(nivel in ("amarillo", "rojo") for nivel in previos)


async def evaluar(
    db: Session,
    usuario: Usuario,
    texto: str,
    sesion_id: str | None = None,
    fuente: str = "conversacion",   # "conversacion" | "dictado" | "creacion"
) -> dict:
    """Devuelve {"nivel", "nivel_efectivo", "mensaje", "ruta_audio"}.

    nivel          el de ESTE texto (es el que se guarda y el que genera señales y alertas).
    nivel_efectivo igual, salvo que sea verde con una señal reciente en la sesión: entonces
                   es "amarillo" (solo cambia cómo responde el modelo; no crea otra alerta).
    mensaje, ruta_audio: solo en ROJO.
    """
    analisis = riesgo.clasificar(texto)
    if analisis.nivel != "verde":
        categorias = ", ".join(analisis.categorias)
        # La señal queda registrada (solo categorías) para poder explicar el semáforo.
        db.add(SenalRiesgo(
            usuario_id=usuario.id, sesion_id=sesion_id, fuente=fuente, nivel=analisis.nivel,
            categorias=categorias, reglas_version=riesgo.REGLAS_VERSION,
        ))
        db.commit()
        alertas.crear_alerta(
            db, usuario, origen="riesgo", nivel=analisis.nivel,
            motivo=f"{categorias} (reglas v{riesgo.REGLAS_VERSION})", sesion_id=sesion_id,
        )
        logger.info("Riesgo %s en sesión %s (%s): %s", analisis.nivel,
                    (sesion_id or "-")[:8], fuente, categorias)

    nivel_efectivo = analisis.nivel
    if analisis.nivel == "verde" and _hubo_senal_reciente(db, sesion_id):
        nivel_efectivo = "amarillo"

    salida: dict = {"nivel": analisis.nivel, "nivel_efectivo": nivel_efectivo,
                    "mensaje": None, "ruta_audio": None}
    if analisis.nivel == "rojo":
        mensaje = riesgo.respuesta_rojo()
        ruta: Path = await asyncio.to_thread(audios_fijos.obtener, "rojo", mensaje)
        salida["mensaje"] = mensaje
        salida["ruta_audio"] = ruta
    return salida