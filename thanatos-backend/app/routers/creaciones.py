"""Cartas y relatos que la persona decide conservar. Solo ve y borra las suyas."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.db import get_db
from app.security import requiere_rol
from app.services import guardia

router = APIRouter(prefix="/creaciones", tags=["creaciones"])

SoloPaciente = Annotated[models.Usuario, Depends(requiere_rol(models.Rol.ADULTO_MAYOR))]
BD = Annotated[Session, Depends(get_db)]


class CreacionIn(BaseModel):
    ejercicio: Literal["cartas_simbolicas", "legado_emocional"]
    texto: str = Field(min_length=1, max_length=8000)
    titulo: str | None = Field(default=None, max_length=120)
    session_id: str | None = None


def _salida(c: models.Creacion) -> dict:
    return {"id": c.id, "ejercicio": c.ejercicio, "titulo": c.titulo,
            "texto": c.texto, "creado_en": c.creado_en}


def _propia(db: Session, usuario: models.Usuario, creacion_id: int) -> models.Creacion:
    creacion = db.get(models.Creacion, creacion_id)
    if creacion is None or creacion.usuario_id != usuario.id:
        raise HTTPException(404, "No encontrado")
    return creacion


@router.post("", status_code=201)
async def guardar(datos: CreacionIn, usuario: SoloPaciente, db: BD):
    if datos.session_id:
        sesion = db.get(models.Sesion, datos.session_id)
        if sesion is None or sesion.usuario_id != usuario.id:
            raise HTTPException(404, "Sesión no encontrada")

    # El texto puede haberse editado después de dictarlo, así que se revisa otra vez.
    revision = await guardia.evaluar(db, usuario, datos.texto, datos.session_id, fuente="creacion")
    creacion = models.Creacion(
        usuario_id=usuario.id, sesion_id=datos.session_id, ejercicio=datos.ejercicio,
        titulo=datos.titulo, texto=datos.texto, riesgo=revision["nivel"],
    )
    db.add(creacion)
    db.commit()

    salida = _salida(creacion)
    salida["mensaje"] = revision["mensaje"]   # solo en rojo: la app debe mostrarlo y reproducirlo
    salida["audio_url"] = f"/audio/{revision['ruta_audio'].name}" if revision["ruta_audio"] else None
    return salida


@router.get("")
def listar(usuario: SoloPaciente, db: BD):
    filas = db.scalars(
        select(models.Creacion)
        .where(models.Creacion.usuario_id == usuario.id)
        .order_by(models.Creacion.id.desc())
    ).all()
    return [_salida(c) for c in filas]


@router.get("/{creacion_id}")
def ver(creacion_id: int, usuario: SoloPaciente, db: BD):
    return _salida(_propia(db, usuario, creacion_id))


@router.delete("/{creacion_id}", status_code=204)
def borrar(creacion_id: int, usuario: SoloPaciente, db: BD):
    """La persona puede borrar lo suyo cuando quiera."""
    db.delete(_propia(db, usuario, creacion_id))
    db.commit()
    return Response(status_code=204)