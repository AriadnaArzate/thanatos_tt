"""Registrar emoción: la persona elige una de las seis emociones de la cuadrícula (2 columnas
por 3 filas). Alimenta al motor conversacional (ver services/contexto.py) y al dashboard."""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.db import get_db
from app.security import requiere_rol
from app.services.contexto import CATALOGO_EMOCIONES, ids_validos

router = APIRouter(prefix="/emociones", tags=["emociones"])

SoloPaciente = Annotated[models.Usuario, Depends(requiere_rol(models.Rol.ADULTO_MAYOR))]
BD = Annotated[Session, Depends(get_db)]


class EmocionIn(BaseModel):
    emocion: str
    # Opcional: la pantalla actual no la pide. Se deja por si se agrega después.
    intensidad: int | None = Field(default=None, ge=1, le=5)


@router.get("/catalogo")
def catalogo(usuario: SoloPaciente):
    """Las seis emociones, en el orden de la cuadrícula (izquierda a derecha, arriba abajo)."""
    return [{"id": e["id"], "etiqueta": e["etiqueta"]} for e in CATALOGO_EMOCIONES]


@router.post("", status_code=201)
def registrar(datos: EmocionIn, usuario: SoloPaciente, db: BD):
    # Solo se acepta una emoción del catálogo y sin texto libre, para que este registro
    # no necesite pasar por la revisión de riesgo.
    if datos.emocion not in ids_validos():
        raise HTTPException(422, "Emoción no válida.")
    registro = models.RegistroEmocion(
        usuario_id=usuario.id, emocion=datos.emocion, intensidad=datos.intensidad
    )
    db.add(registro)
    db.commit()
    return {"id": registro.id, "emocion": registro.emocion,
            "intensidad": registro.intensidad, "creado_en": registro.creado_en}


@router.get("/mias")
def mis_emociones(usuario: SoloPaciente, db: BD, dias: int = 30):
    desde = datetime.now(timezone.utc) - timedelta(days=dias)
    filas = db.scalars(
        select(models.RegistroEmocion)
        .where(models.RegistroEmocion.usuario_id == usuario.id,
               models.RegistroEmocion.creado_en >= desde)
        .order_by(models.RegistroEmocion.id.desc())
    ).all()
    return [{"id": r.id, "emocion": r.emocion, "intensidad": r.intensidad,
             "creado_en": r.creado_en} for r in filas]