"""Alta y listado de pacientes solo lo hace el TANATOLOGO"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Rol, Usuario
from app.schemas import NuevoUsuarioIn, UsuarioOut
from app.security import hashear_password, hashear_password, requiere_rol

router = APIRouter(prefix="/pacientes", tags=["pacientes"])

SoloTanatologo = Annotated[Usuario, Depends(requiere_rol(Rol.TANATOLOGO))]

@router.post("", response_model=UsuarioOut, status_code=201)
def crear_paciente(datos: NuevoUsuarioIn, tanatologo: SoloTanatologo, db: Annotated[Session, Depends(get_db)]):
    nombre_usuario = datos.usuario.strip().lower()
    if db.scalar(select(Usuario).where(Usuario.usuario == nombre_usuario)):
        raise HTTPException(409, "El nombre de usuario ya existe, intente con otro")
    paciente = Usuario(
        nombre=datos.nombre.strip(),
        usuario=nombre_usuario,
        password_hash=hashear_password(datos.password),
        rol=Rol.ADULTO_MAYOR.value,
        tanatologo_id=tanatologo.id, #queda asignado a quien lo da de alta

    )
    db.add(paciente)
    db.commit()
    return paciente
@router.get("", response_model=list[UsuarioOut])
def listar_pacientes(tanatologo: SoloTanatologo, db: Annotated[Session, Depends(get_db)]):
    """Solo los pacientes de este tanatólogo."""
    return db.scalars(select(Usuario).where(Usuario.tanatologo_id == tanatologo.id)).all()
