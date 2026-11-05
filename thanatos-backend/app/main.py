"""
Backend de Thanatos - ciclo de voz + usuarios, roles, sesiones en SQLite y
ejemplos de estilo del dataset semilla.

    audio del adulto mayor (con token)
        -> Whisper (ASR)  : audio -> texto
        -> Ejemplos       : se buscan ejemplos de estilo parecidos
        -> Ollama  (NLP)  : texto + ejemplos -> respuesta
        -> TTS            : respuesta -> audio
        -> SQLite         : se guardan sesión y mensajes

Todavía NO hay: clasificación de riesgo (RN-08), alertas ni ejercicios.

Arranque (desde thanatos-backend):  uvicorn app.main:app --reload
Docs interactivas: http://localhost:8000/docs
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.db import Base, engine, get_db
from app.routers import auth, pacientes
from app.security import requiere_rol
from app.services import asr, ejemplos, llm, tts

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("thanatos.main")

# Se dice cuando Whisper no detecta habla (silencio, ruido, audio corto).
MENSAJE_NO_ENTENDI = "Disculpe, no alcancé a escucharle bien. ¿Podría repetirlo, por favor?"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Al arrancar: crea carpetas y tablas, y calienta los modelos."""
    settings.audio_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)   # crea thanatos.db y las tablas si no existen
    if settings.jwt_secret == "CAMBIAR-EN-ENV":
        logger.warning("JWT_SECRET sin definir: cualquiera podría falsificar tokens. "
                       "Defínela en .env antes de usar datos reales.")
    await asyncio.to_thread(asr.precargar_modelo)
    if not await llm.ollama_disponible():
        logger.warning("Ollama NO responde en %s. Ábrelo y descarga el modelo: "
                       "ollama pull %s", settings.ollama_host, settings.ollama_model)
    await ejemplos.cargar_indice()     # lee el dataset semilla y calcula sus embeddings
    if not Path(settings.piper_voice_path).exists():
        logger.warning("No se encontró la voz de Piper en '%s' (solo se usa como respaldo).",
                       settings.piper_voice_path)
    yield


app = FastAPI(title="Thanatos - motor conversacional", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(pacientes.router)


@app.get("/salud")
async def salud():
    """Revisión rápida de que cada pieza está lista (sin datos sensibles)."""
    return {
        "whisper_cargado": asr._modelo is not None,  # noqa: SLF001
        "ollama": await llm.ollama_disponible(),
        "voz_piper": Path(settings.piper_voice_path).exists(),
    }


# ---------------------------------------------------------------------------
# Ayudantes de sesión / historial
# ---------------------------------------------------------------------------
def _obtener_o_crear_sesion(db: Session, usuario: models.Usuario, session_id: str | None) -> models.Sesion:
    """Reanuda una sesión del propio usuario o crea una nueva."""
    if session_id:
        sesion = db.get(models.Sesion, session_id)
        # 404 (y no 403) también si es de otro usuario: así no se revela que existe.
        if sesion is None or sesion.usuario_id != usuario.id:
            raise HTTPException(404, "Sesión no encontrada")
        return sesion
    sesion = models.Sesion(id=uuid4().hex, usuario_id=usuario.id)
    db.add(sesion)
    db.commit()
    return sesion


def _cargar_historial(db: Session, sesion_id: str) -> list[dict]:
    """Últimos N turnos de la sesión, en orden cronológico y formato de chat."""
    filas = db.scalars(
        select(models.Mensaje)
        .where(models.Mensaje.sesion_id == sesion_id)
        .order_by(models.Mensaje.id.desc())
        .limit(settings.max_history_turns * 2)
    ).all()
    return [{"role": m.rol, "content": m.texto} for m in reversed(filas)]


# ---------------------------------------------------------------------------
# Endpoint principal
# ---------------------------------------------------------------------------
@app.post("/conversar")
async def conversar(
    usuario: Annotated[models.Usuario, Depends(requiere_rol(models.Rol.ADULTO_MAYOR))],
    db: Annotated[Session, Depends(get_db)],
    audio: UploadFile = File(..., description="Audio del usuario (wav, m4a, mp3...)"),
    session_id: str | None = Form(None, description="Vacío en el primer turno"),
):
    """Un turno de conversación. Solo para usuarios con rol adulto_mayor."""
    tiempos: dict[str, float] = {}
    inicio_total = time.perf_counter()

    sesion = _obtener_o_crear_sesion(db, usuario, session_id)

    # 1) Guardar el audio recibido en un archivo temporal.
    sufijo = Path(audio.filename or "").suffix or ".m4a"
    ruta_entrada = settings.audio_dir / f"in_{uuid4().hex}{sufijo}"
    ruta_entrada.write_bytes(await audio.read())

    # 2) ASR: voz -> texto (bloqueante, va a un hilo aparte).
    try:
        t0 = time.perf_counter()
        texto_usuario = await asyncio.to_thread(asr.transcribir, ruta_entrada)
        tiempos["asr_s"] = round(time.perf_counter() - t0, 2)
    finally:
        ruta_entrada.unlink(missing_ok=True)  # no acumulamos audios de usuarios

    # 3) NLP: texto -> respuesta.
    if not texto_usuario:
        # No hubo habla reconocible: no llamamos al LLM ni guardamos nada.
        texto_respuesta = MENSAJE_NO_ENTENDI
        tiempos["llm_s"] = 0.0
    else:
        historial = _cargar_historial(db, sesion.id)
        historial.append({"role": "user", "content": texto_usuario})

        # 3a) Ejemplos de estilo parecidos a lo que dijo la persona (dataset semilla).
        t0 = time.perf_counter()
        usados = await ejemplos.buscar(texto_usuario)
        tiempos["ejemplos_s"] = round(time.perf_counter() - t0, 2)
        if usados:
            logger.info("Ejemplos usados: %s", [(e.id, e.marco) for e in usados])

        # 3b) Respuesta del LLM.
        try:
            t0 = time.perf_counter()
            texto_respuesta = await llm.generar_respuesta(
                historial, ejemplos.formatear_para_prompt(usados)
            )
            tiempos["llm_s"] = round(time.perf_counter() - t0, 2)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Falló Ollama")
            raise HTTPException(503, "El motor conversacional no está disponible.") from exc

        # Guardamos el turno COMPLETO solo si el LLM respondió (así no quedan
        # mensajes del usuario "huérfanos" sin respuesta).
        db.add_all([
            models.Mensaje(sesion_id=sesion.id, rol="user", texto=texto_usuario),
            models.Mensaje(sesion_id=sesion.id, rol="assistant", texto=texto_respuesta),
        ])
        db.commit()

    # 4) TTS: respuesta -> audio (la extensión la decide el proveedor).
    base_audio = settings.audio_dir / f"resp_{uuid4().hex}"
    try:
        t0 = time.perf_counter()
        ruta_audio = await asyncio.to_thread(tts.sintetizar, texto_respuesta, base_audio)
        tiempos["tts_s"] = round(time.perf_counter() - t0, 2)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falló el TTS")
        raise HTTPException(503, "No se pudo generar la voz de respuesta.") from exc

    tiempos["total_s"] = round(time.perf_counter() - inicio_total, 2)
    logger.info("Turno %s | tiempos: %s", sesion.id[:8], tiempos)

    return {
        "session_id": sesion.id,
        "texto_usuario": texto_usuario,
        "texto_respuesta": texto_respuesta,
        "audio_url": f"/audio/{ruta_audio.name}",
        "tiempos": tiempos,
    }


@app.get("/audio/{nombre}")
async def obtener_audio(nombre: str):
    """Sirve el audio generado (.mp3 de edge-tts o .wav de Piper).

    OJO: por ahora NO pide token; se protege solo con el nombre aleatorio
    (uuid). Pendiente endurecerlo. `Path(nombre).name` evita rutas como ../../x.
    """
    ruta = settings.audio_dir / Path(nombre).name
    if not ruta.is_file():
        raise HTTPException(404, "Audio no encontrado")

    tipo = "audio/mpeg" if ruta.suffix == ".mp3" else "audio/wav"
    return FileResponse(ruta, media_type=tipo)

# TODO: los audios de respuesta se acumulan en tmp_audio/. Falta limpieza periódica.