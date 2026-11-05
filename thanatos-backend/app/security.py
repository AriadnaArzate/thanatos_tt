"""Contraseñas, tokens y control de acceso por rol."""
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Rol, Usuario

# Le dice a FastAPI dónde se obtiene el token (y habilita el botón "Authorize" en /docs).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hashear_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:  # hash mal formado
        return False


def crear_token(usuario: Usuario) -> str:
    """JWT firmado. Solo lleva el id (sub) y la expiración; el rol real se lee
    de la BD en cada petición, así un cambio de rol o una baja aplican al instante."""
    expira = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expira_minutos)
    return jwt.encode(
        {"sub": str(usuario.id), "exp": expira},
        settings.jwt_secret,
        algorithm=settings.jwt_algoritmo,
    )


def usuario_actual(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Usuario:
    """Dependencia: devuelve el usuario dueño del token o responde 401."""
    error = HTTPException(401, "Credenciales inválidas", headers={"WWW-Authenticate": "Bearer"})
    try:
        datos = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algoritmo])
        usuario_id = int(datos["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise error from None
    usuario = db.get(Usuario, usuario_id)
    if usuario is None or not usuario.activo:
        raise error
    return usuario


def requiere_rol(*roles: Rol):
    """Fábrica de dependencias: exige que el usuario tenga uno de los roles dados."""
    permitidos = {r.value for r in roles}

    def dependencia(usuario: Annotated[Usuario, Depends(usuario_actual)]) -> Usuario:
        if usuario.rol not in permitidos:
            raise HTTPException(403, "No tiene permiso para esta acción")
        return usuario

    return dependencia
