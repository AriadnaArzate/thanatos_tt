"""Contactar a mi tanatólogo: crea una alerta para el tanatólogo asignado."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models
from app.db import get_db
from app.security import requiere_rol
from app.services import alertas

router = APIRouter(prefix="/contacto", tags=["contacto"])

SoloPaciente = Annotated[models.Usuario, Depends(requiere_rol(models.Rol.ADULTO_MAYOR))]
BD = Annotated[Session, Depends(get_db)]


class SolicitudContacto(BaseModel):
    # Opciones fijas (sin texto libre). La app puede ofrecerlas como botones. [VALIDAR]
    motivo: Literal["hablar", "necesito_ayuda_hoy", "otro"] = "hablar"


@router.post("/tanatologo")
def contactar(datos: SolicitudContacto, usuario: SoloPaciente, db: BD):
    if usuario.tanatologo_id is None:
        raise HTTPException(409, "Todavía no tiene un tanatólogo asignado.")
    alerta = alertas.crear_alerta(
        db, usuario, origen="contacto", nivel="contacto", motivo=datos.motivo
    )
    return {"mensaje": "Ya le avisé a su tanatólogo.", "alerta_id": alerta.id}