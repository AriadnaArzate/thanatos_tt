"""Inicio de sesión, registro de tanatólogos y perfil propio."""
import hmac
import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Rol, Usuario
from app.schemas import PerfilIn, RegistroTanatologoIn, TokenOut, UsuarioOut
from app.security import crear_token, hashear_password, usuario_actual, verificar_password

router = APIRouter(prefix="/auth", tags=["auth"])

# Límite de intentos fallidos de inicio de sesión por IP (en memoria: se reinicia con el
# servidor). Un ID y un PIN de 6 dígitos son adivinables por fuerza bruta; esto lo frena.
_MAX_FALLOS = 10
_VENTANA_SEG = 10 * 60
_fallos: dict[str, deque] = defaultdict(deque)


def _ip(request: Request) -> str:
    return request.client.host if request.client else "desconocida"


def _revisar_limite(ip: str) -> None:
    ahora = time.monotonic()
    cola = _fallos[ip]
    while cola and ahora - cola[0] > _VENTANA_SEG:
        cola.popleft()
    if len(cola) >= _MAX_FALLOS:
        raise HTTPException(429, "Demasiados intentos. Espere unos minutos e intente de nuevo.")


@router.post("/login", response_model=TokenOut)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    """Inicio de sesión para todos con el mismo formulario (username / password).

    - Tanatólogo: su correo y su contraseña.
    - Adulto mayor: su ID de paciente y el PIN de 6 dígitos (ambos se los da su tanatólogo).
    """
    ip = _ip(request)
    _revisar_limite(ip)
    # Minúsculas y sin espacios: el teclado del celular suele capitalizar la primera letra.
    entrada = form.username.strip().lower()
    usuario = db.scalar(select(Usuario).where(Usuario.usuario == entrada))
    # Mismo mensaje para "no existe" y "contraseña mala": no revelamos cuál fue.
    if usuario is None or not usuario.activo or not verificar_password(form.password, usuario.password_hash):
        _fallos[ip].append(time.monotonic())
        raise HTTPException(401, "Usuario o contraseña incorrectos", headers={"WWW-Authenticate": "Bearer"})
    _fallos.pop(ip, None)
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

    correo = datos.correo.strip().lower()
    if db.scalar(select(Usuario).where(Usuario.usuario == correo)):
        raise HTTPException(409, "Ese correo ya está registrado.")

    tanatologo = Usuario(
        nombre=datos.nombre.strip(),
        usuario=correo,        # el correo es el usuario para iniciar sesión
        correo=correo,
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


@router.patch("/yo", response_model=UsuarioOut)
def editar_yo(
    datos: PerfilIn,
    usuario: Annotated[Usuario, Depends(usuario_actual)],
    db: Annotated[Session, Depends(get_db)],
):
    """Pantalla "Información del Tanatólogo": guardar cambios de nombre, correo y teléfono.
    Solo para tanatólogos; los pacientes no editan su perfil desde la app."""
    if usuario.rol != Rol.TANATOLOGO.value:
        raise HTTPException(403, "No tiene permiso para esta acción")

    if datos.nombre is not None:
        usuario.nombre = datos.nombre.strip()
    if datos.telefono is not None:
        usuario.telefono = datos.telefono.strip() or None
    if datos.correo is not None:
        nuevo = datos.correo.strip().lower()
        if nuevo != usuario.usuario:
            if db.scalar(select(Usuario).where(Usuario.usuario == nuevo)):
                raise HTTPException(409, "Ese correo ya está registrado.")
            # El correo es el usuario de acceso: cambiarlo cambia con qué se inicia sesión.
            usuario.usuario = nuevo
        usuario.correo = nuevo
    db.commit()
    db.refresh(usuario)
    return usuario