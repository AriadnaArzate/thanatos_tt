"""Inicio de sesión."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Usuario
from app.schemas import TokenOut, UsuarioOut
from app.security import crear_token, usuario_actual, verificar_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    # Minúsculas y sin espacios: el teclado del celular suele capitalizar la primera letra.
    nombre_usuario = form.username.strip().lower()
    usuario = db.scalar(select(Usuario).where(Usuario.usuario == nombre_usuario))
    # Mismo mensaje para "no existe" y "contraseña incorrecta": no revelamos cuál fue.
    if usuario is None or not usuario.activo or not verificar_password(form.password, usuario.password_hash):
        raise HTTPException(401, "Usuario o contraseña incorrectos", headers={"WWW-Authenticate": "Bearer"})
    return TokenOut(access_token=crear_token(usuario))


@router.get("/yo", response_model=UsuarioOut)
def yo(usuario: Annotated[Usuario, Depends(usuario_actual)]):
    """Quién soy según mi token (útil para que la app sepa qué vista mostrar)."""
    return usuario