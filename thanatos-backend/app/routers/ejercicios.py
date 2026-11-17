"""Ejercicios de desahogo: cada vez que la persona abre la opción, se elige uno al azar y
el motor conversacional se lo explica en voz. El ejercicio NO se hace dentro de la aplicación."""
import asyncio
import logging
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.db import get_db
from app.security import requiere_rol
from app.services import audios_fijos, contexto, ejercicios, llm, tts

logger = logging.getLogger("thanatos.ejercicios")

router = APIRouter(prefix="/ejercicios", tags=["ejercicios"])

SoloPaciente = Annotated[models.Usuario, Depends(requiere_rol(models.Rol.ADULTO_MAYOR))]
BD = Annotated[Session, Depends(get_db)]


@router.post("/desahogo")
async def sugerir_ejercicio(usuario: SoloPaciente, db: BD):
    """Elige un ejercicio al azar (distinto del último que se le mostró) y lo explica en voz.

    Tarda como una respuesta del modelo: la app debe mostrar "pensando...". Si el modelo no
    está disponible, se usa una explicación fija del mismo ejercicio.
    """
    ultimo = db.scalar(
        select(models.EjercicioMostrado.ejercicio)
        .where(models.EjercicioMostrado.usuario_id == usuario.id)
        .order_by(models.EjercicioMostrado.id.desc())
        .limit(1)
    )
    ejercicio = ejercicios.sortear(excluir=ultimo)

    # La emoción que la persona registró hace poco ajusta el tono de la explicación.
    registro = contexto.emocion_reciente(db, usuario.id)
    emocion = contexto.para_el_modelo(registro.emocion) if registro else None

    try:
        explicacion = await llm.explicar_ejercicio(
            ejercicio.nombre, ejercicio.objetivo, ejercicio.pasos, ejercicio.duracion, emocion
        )
        texto = f"{explicacion} {ejercicios.CIERRE}"
        origen = "modelo"
    except Exception:  # noqa: BLE001 - modelo caído, explicación con tuteo o demasiado corta
        logger.exception("Se usa la explicación de respaldo del ejercicio %s", ejercicio.id)
        texto = ejercicios.respaldo_completo(ejercicio)
        origen = "respaldo"

    try:
        if origen == "respaldo":
            # El texto fijo tiene su audio guardado: responde al instante.
            ruta = await asyncio.to_thread(audios_fijos.obtener, f"ejercicio_{ejercicio.id}", texto)
        else:
            base = settings.audio_dir / f"resp_{uuid4().hex}"
            ruta = await asyncio.to_thread(tts.sintetizar, texto, base)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falló el TTS del ejercicio")
        raise HTTPException(503, "No se pudo generar la voz de la explicación.") from exc

    db.add(models.EjercicioMostrado(usuario_id=usuario.id, ejercicio=ejercicio.id))
    db.commit()
    return {
        "ejercicio": {"id": ejercicio.id, "nombre": ejercicio.nombre},
        "texto": texto,
        "audio_url": f"/audio/{ruta.name}",
        "origen": origen,
    }