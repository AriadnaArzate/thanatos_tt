"""Guía auditiva: narración del menú (botón de sonido) y lectura de textos en voz alta."""
import asyncio
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app import models
from app.config import settings
from app.security import requiere_rol
from app.services import audios_fijos, tts

router = APIRouter(prefix="/guia", tags=["guia"])

SoloPaciente = Annotated[models.Usuario, Depends(requiere_rol(models.Rol.ADULTO_MAYOR))]

# Opciones del menú (como se ven en la app) y lo que se dice al narrarlas. [VALIDAR los textos]
MENU = [
    {"id": "hablar", "texto": "Hablar ahora",
     "guia": "Hablar ahora. Toque este botón para conversar conmigo."},
    {"id": "ejercicio", "texto": "Ejercicios de desahogo",
     "guia": "Ejercicios de desahogo. Le explico un ejercicio para expresar lo que siente."},
    {"id": "emocion", "texto": "Registrar emoción",
     "guia": "Registrar emoción. Elija cómo se siente hoy."},
    {"id": "tanatologo", "texto": "Contactar a mi tanatólogo",
     "guia": "Contactar a mi tanatólogo. Le avisaremos a su tanatólogo."},
    {"id": "salir", "texto": "Cerrar sesión",
     "guia": "Cerrar sesión. Termina su sesión en esta aplicación."},
]


def precalentar_menu() -> None:
    """Genera de antemano los audios del menú. Se llama al arrancar (en segundo plano)."""
    audios_fijos.precalentar({f"menu_{o['id']}": o["guia"] for o in MENU})


@router.get("/menu")
async def menu(usuario: SoloPaciente):
    """Cada opción con su texto y el audio de su narración."""
    opciones = []
    for o in MENU:
        ruta = await asyncio.to_thread(audios_fijos.obtener, f"menu_{o['id']}", o["guia"])
        opciones.append({"id": o["id"], "texto": o["texto"], "guia": o["guia"],
                         "audio_url": f"/audio/{ruta.name}"})
    return opciones


class LeerIn(BaseModel):
    texto: str = Field(min_length=1, max_length=1500)


@router.post("/leer")
async def leer(datos: LeerIn, usuario: SoloPaciente):
    """Convierte un texto en audio para escucharlo."""
    base = settings.audio_dir / f"resp_{uuid4().hex}"
    ruta = await asyncio.to_thread(tts.sintetizar, datos.texto, base)
    return {"audio_url": f"/audio/{ruta.name}"}