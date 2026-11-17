"""Inicio de sesión y registro de tanatólogos."""
import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Rol, Usuario
from app.schemas import RegistroTanatologoIn, TokenOut, UsuarioOut
from app.security import crear_token, hashear_password, usuario_actual, verificar_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    # Minúsculas y sin espacios: el teclado del celular suele capitalizar la primera letra.
    nombre_usuario = form.username.strip().lower()
    usuario = db.scalar(select(Usuario).where(Usuario.usuario == nombre_usuario))
    # Mismo mensaje para "no existe" y "contraseña mala": no revelamos cuál fue.
    if usuario is None or not usuario.activo or not verificar_password(form.password, usuario.password_hash):
        raise HTTPException(401, "Usuario o contraseña incorrectos", headers={"WWW-Authenticate": "Bearer"})
    return TokenOut(access_token=crear_token(usuario))


@router.post("/registro-tanatologo", response_model=TokenOut, status_code=201)
def registro_tanatologo(datos: RegistroTanatologoIn, db: Annotated[Session, Depends(get_db)]):
    """Un tanatólogo crea su propia cuenta desde la pantalla de inicio de sesión.
    Devuelve el token, así que la app puede entrar de inmediato.

    PENDIENTE (trabajo a futuro): verificar que quien se registra sea realmente un
    tanatólogo. Mientras tanto, si CODIGO_REGISTRO_TANATOLOGO está definido en el
    .env, se exige ese código; si está vacío, el registro es abierto.
    Esta cuenta solo ve a los pacientes que ella misma dé de alta."""
    codigo_requerido = settings.codigo_registro_tanatologo
    if codigo_requerido and not hmac.compare_digest(
        (datos.codigo or "").encode("utf-8"), codigo_requerido.encode("utf-8")
    ):
        raise HTTPException(403, "Código de registro incorrecto.")

    nombre_usuario = datos.usuario.strip().lower()
    if db.scalar(select(Usuario).where(Usuario.usuario == nombre_usuario)):
        raise HTTPException(409, "Ese nombre de usuario ya existe.")

    tanatologo = Usuario(
        nombre=datos.nombre.strip(),
        usuario=nombre_usuario,
        password_hash=hashear_password(datos.password),
        rol=Rol.TANATOLOGO.value,
        telefono=datos.telefono.strip() if datos.telefono else None,
    )
    db.add(tanatologo)
    db.commit()
    return TokenOut(access_token=crear_token(tanatologo))


@router.get("/yo", response_model=UsuarioOut)
def yo(usuario: Annotated[Usuario, Depends(usuario_actual)]):
    """Quién soy según mi token (útil para que la app sepa qué vista mostrar)."""
    return usuario