"""
Backend de Thanatos: ciclo de voz, usuarios y roles, ejercicios de desahogo, riesgo y alertas.

    audio del adulto mayor
        -> Whisper (ASR)  : audio -> texto (y cuánto tiempo habló)
        -> Riesgo         : verde / amarillo / rojo (rojo NO pasa por el modelo)
        -> Contexto       : emoción registrada hoy + ejemplos de estilo (dataset semilla)
        -> Ollama  (NLP)  : texto + contexto -> respuesta
        -> TTS            : respuesta -> audio
        -> SQLite         : sesión, mensajes, alertas

LÍMITE DE TIEMPO: "Hablar ahora" admite como máximo LIMITE_CONVERSACION_MINUTOS
(20 por defecto) de audio hablado por la persona en cada conversación; lo que dice
el asistente no cuenta.

Arranque (desde thanatos-backend):  uvicorn app.main:app --reload
Para probar desde un teléfono:      uvicorn app.main:app --host 0.0.0.0 --port 8000
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

from app import migraciones, models
from app.config import settings
from app.db import get_db
from app.routers import auth, contacto, dashboard, emociones, guia, pacientes
from app.routers import ejercicios as router_ejercicios
from app.security import requiere_rol
from app.services import asr, audios_fijos, contexto, ejemplos, guardia, llm, riesgo, tts
from app.services import ejercicios as catalogo_ejercicios

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("thanatos.main")

# Se dice cuando Whisper no detecta habla (silencio, ruido, audio corto).
MENSAJE_NO_ENTENDI = "Disculpe, no alcancé a escucharle bien. ¿Podría repetirlo, por favor?"

# Se dice al llegar al límite de tiempo de la conversación. [VALIDAR los textos]
MENSAJE_LIMITE = (
    "Hemos llegado al tiempo de nuestra conversación de hoy. Gracias por compartir conmigo. "
    "Si lo necesita, puede hablar con su tanatólogo o hacer un ejercicio para desahogarse desde el menú."
)
# Se agrega al final de la respuesta del turno en el que se alcanza el límite.
MENSAJE_CIERRE = "Con esto llegamos al tiempo de nuestra conversación. Gracias por compartir conmigo."

# Limpieza de audios: las respuestas habladas pueden repetir lo que contó la persona,
# así que no se conservan. Se borran las que tengan más de AUDIO_VIGENCIA_MIN minutos.
# Los audios fijos ("fijo_...": menú, ejercicios, rojo, límite) NO se borran nunca.
AUDIO_VIGENCIA_MIN = 15
_CADA_CUANTO_LIMPIAR_S = 5 * 60


def _limpiar_audios_viejos() -> int:
    """Borra de la carpeta de audios los archivos que no son fijos y tienen más de
    AUDIO_VIGENCIA_MIN minutos. Devuelve cuántos borró. Nunca lanza errores."""
    limite = time.time() - AUDIO_VIGENCIA_MIN * 60
    borrados = 0
    for ruta in settings.audio_dir.glob("*"):
        try:
            if ruta.is_file() and not ruta.name.startswith("fijo_") and ruta.stat().st_mtime < limite:
                ruta.unlink()
                borrados += 1
        except OSError:  # p. ej. el archivo se está reproduciendo o ya se borró
            continue
    return borrados


async def _limpiar_periodicamente() -> None:
    """Tarea en segundo plano: limpia los audios viejos cada cierto tiempo."""
    while True:
        await asyncio.sleep(_CADA_CUANTO_LIMPIAR_S)
        borrados = await asyncio.to_thread(_limpiar_audios_viejos)
        if borrados:
            logger.info("Limpieza: se borraron %d audios de respuesta antiguos.", borrados)


def _precalentar_audios_fijos() -> None:
    """Genera de antemano los audios que se repiten (menú, explicaciones de respaldo de los
    ejercicios, mensaje de riesgo rojo y de límite de tiempo)."""
    guia.precalentar_menu()
    audios_fijos.precalentar(
        {f"ejercicio_{e.id}": catalogo_ejercicios.respaldo_completo(e)
         for e in catalogo_ejercicios.listar()}
        | {"rojo": riesgo.respuesta_rojo(), "limite": MENSAJE_LIMITE}
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Al arrancar: crea carpetas, tablas y columnas nuevas, y calienta los modelos."""
    settings.audio_dir.mkdir(parents=True, exist_ok=True)
    borrados = _limpiar_audios_viejos()   # restos de ejecuciones anteriores
    if borrados:
        logger.info("Limpieza al arrancar: se borraron %d audios de respuesta antiguos.", borrados)
    migraciones.aplicar()   # crea tablas nuevas y agrega columnas que falten
    if settings.jwt_secret == "CAMBIAR-EN-ENV":
        logger.warning("JWT_SECRET sin definir: cualquiera podría falsificar tokens. "
                       "Defínela en .env antes de usar datos reales.")
    await asyncio.to_thread(asr.precargar_modelo)
    if not await llm.ollama_disponible():
        logger.warning("Ollama NO responde en %s. Ábrelo y descarga el modelo: "
                       "ollama pull %s", settings.ollama_host, settings.ollama_model)
    await ejemplos.cargar_indice()     # lee el dataset semilla y calcula sus embeddings
    # Los audios fijos se generan en segundo plano para no retrasar el arranque.
    app.state.tarea_audios = asyncio.create_task(asyncio.to_thread(_precalentar_audios_fijos))
    if not Path(settings.piper_voice_path).exists():
        logger.warning("No se encontró la voz de Piper en '%s' (solo se usa como respaldo).",
                       settings.piper_voice_path)
    app.state.tarea_limpieza = asyncio.create_task(_limpiar_periodicamente())
    yield
    app.state.tarea_limpieza.cancel()   # al apagar el servidor


app = FastAPI(title="Thanatos - motor conversacional", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(pacientes.router)
app.include_router(router_ejercicios.router)
app.include_router(emociones.router)
app.include_router(contacto.router)
app.include_router(guia.router)
app.include_router(dashboard.router)


@app.get("/salud")
async def salud():
    """Revisión rápida de que cada pieza está lista (sin datos sensibles)."""
    return {
        "whisper_cargado": asr._modelo is not None,  # noqa: SLF001
        "ollama": await llm.ollama_disponible(),
        "voz_piper": Path(settings.piper_voice_path).exists(),
        "reglas_riesgo": riesgo.REGLAS_VERSION,
        "limite_conversacion_minutos": settings.limite_conversacion_minutos,
    }


# ---------------------------------------------------------------------------
# Ayudantes de sesión / historial / tiempo
# ---------------------------------------------------------------------------
def _obtener_o_crear_sesion(db: Session, usuario: models.Usuario, session_id: str | None) -> models.Sesion:
    """Reanuda una sesión del propio usuario o crea una nueva."""
    if session_id:
        sesion = db.get(models.Sesion, session_id)
        # 404 (y no 403) también si es de otro usuario: así no se revela que existe.
        if sesion is None or sesion.usuario_id != usuario.id:
            raise HTTPException(404, "Sesión no encontrada")
        return sesion
    sesion = models.Sesion(id=uuid4().hex, usuario_id=usuario.id, tipo="conversacion")
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


def _limite_segundos() -> int | None:
    """Límite de cada conversación en segundos (None si se desactivó con
    LIMITE_CONVERSACION_MINUTOS=0)."""
    if settings.limite_conversacion_minutos <= 0:
        return None
    return settings.limite_conversacion_minutos * 60


def _tiempo(sesion: models.Sesion, limite_s: int | None) -> dict:
    """Lo que la app necesita para mostrar el tiempo (segundos hablados por la persona)."""
    usados = round(sesion.segundos_usuario or 0.0)
    return {
        "segundos_usados": usados,
        "limite_segundos": limite_s,
        "segundos_restantes": None if limite_s is None else max(0, limite_s - usados),
    }


async def _respuesta_limite(sesion: models.Sesion, limite_s: int) -> dict:
    """Respuesta cuando la conversación ya llegó al límite: no se procesa el audio."""
    ruta = await asyncio.to_thread(audios_fijos.obtener, "limite", MENSAJE_LIMITE)
    return {
        "session_id": sesion.id,
        "texto_usuario": "",
        "texto_respuesta": MENSAJE_LIMITE,
        "audio_url": f"/audio/{ruta.name}",
        "tiempos": {},
        "tiempo_conversacion": _tiempo(sesion, limite_s),
        "limite_alcanzado": True,
    }


# ---------------------------------------------------------------------------
# Endpoint principal: "Hablar ahora"
# ---------------------------------------------------------------------------
@app.post("/conversar")
async def conversar(
    usuario: Annotated[models.Usuario, Depends(requiere_rol(models.Rol.ADULTO_MAYOR))],
    db: Annotated[Session, Depends(get_db)],
    audio: UploadFile = File(..., description="Audio del usuario (wav, m4a, mp3...)"),
    session_id: str | None = Form(None, description="Vacío en el primer turno"),
):
    """Un turno de conversación. Solo para adultos mayores."""
    tiempos: dict[str, float] = {}
    inicio_total = time.perf_counter()

    sesion = _obtener_o_crear_sesion(db, usuario, session_id)

    # Límite de tiempo: si ya se agotó, no se procesa el audio. Excepción: si en la sesión
    # hubo señales de riesgo, NO se corta la conversación por tiempo.
    limite_s = _limite_segundos()
    if (limite_s is not None and (sesion.segundos_usuario or 0.0) >= limite_s
            and not guardia.hay_senal_reciente(db, sesion.id)):
        return await _respuesta_limite(sesion, limite_s)

    # 1) Guardar el audio recibido en un archivo temporal.
    sufijo = Path(audio.filename or "").suffix or ".m4a"
    ruta_entrada = settings.audio_dir / f"in_{uuid4().hex}{sufijo}"
    ruta_entrada.write_bytes(await audio.read())

    # 2) ASR: voz -> texto y duración (bloqueante, va a un hilo aparte).
    try:
        t0 = time.perf_counter()
        texto_usuario, segundos_audio = await asyncio.to_thread(
            asr.transcribir_con_duracion, ruta_entrada
        )
        tiempos["asr_s"] = round(time.perf_counter() - t0, 2)
    finally:
        ruta_entrada.unlink(missing_ok=True)  # no acumulamos audios de usuarios

    # Se suma el tiempo que la persona habló (aunque no se haya entendido nada).
    sesion.segundos_usuario = (sesion.segundos_usuario or 0.0) + segundos_audio
    db.commit()

    # 3) Riesgo y respuesta.
    ruta_audio: Path | None = None   # solo se llena si la respuesta es un audio fijo
    limite_alcanzado = False
    if not texto_usuario:
        # No hubo habla reconocible: no llamamos al modelo ni guardamos nada.
        texto_respuesta = MENSAJE_NO_ENTENDI
        tiempos["llm_s"] = 0.0
    else:
        # 3a) Revisión de riesgo ANTES del modelo. Si es amarillo o rojo ya queda la alerta.
        revision = await guardia.evaluar(db, usuario, texto_usuario, sesion.id)
        nivel = revision["nivel"]

        if nivel == "rojo":
            # El modelo de lenguaje NO interviene: se usa el texto fijo aprobado.
            texto_respuesta = revision["mensaje"]
            ruta_audio = revision["ruta_audio"]
            tiempos["llm_s"] = 0.0
        else:
            historial = _cargar_historial(db, sesion.id)
            historial.append({"role": "user", "content": texto_usuario})

            # 3b) Ejemplos de estilo del dataset semilla.
            t0 = time.perf_counter()
            usados = await ejemplos.buscar(texto_usuario)
            tiempos["ejemplos_s"] = round(time.perf_counter() - t0, 2)
            if usados:
                logger.info("Ejemplos usados: %s", [(e.id, e.marco) for e in usados])

            # 3c) Instrucciones extra: la emoción que registró hoy y, si hay señales, cautela.
            extra = []
            nota_emocion = contexto.nota_emocional(db, usuario.id)
            if nota_emocion:
                extra.append(nota_emocion)
            if revision["nivel_efectivo"] == "amarillo":
                extra.append(riesgo.NOTA_AMARILLO)

            # 3d) Respuesta del modelo.
            try:
                t0 = time.perf_counter()
                texto_respuesta = await llm.generar_respuesta(
                    historial, ejemplos.formatear_para_prompt(usados), "\n\n".join(extra)
                )
                tiempos["llm_s"] = round(time.perf_counter() - t0, 2)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Falló Ollama")
                raise HTTPException(503, "El motor conversacional no está disponible.") from exc

            # Si con este turno se alcanza el límite, la respuesta se cierra con un aviso.
            # Con señales de riesgo en la sesión (nivel_efectivo distinto de verde) no se cierra.
            if (limite_s is not None and sesion.segundos_usuario >= limite_s
                    and revision["nivel_efectivo"] == "verde"):
                texto_respuesta = f"{texto_respuesta} {MENSAJE_CIERRE}"
                limite_alcanzado = True

        # Guardamos el turno COMPLETO solo si hubo respuesta. El nivel de riesgo queda
        # en el mensaje del usuario.
        db.add_all([
            models.Mensaje(sesion_id=sesion.id, rol="user", texto=texto_usuario, riesgo=nivel),
            models.Mensaje(sesion_id=sesion.id, rol="assistant", texto=texto_respuesta),
        ])
        db.commit()

    # 4) TTS: respuesta -> audio (la extensión la decide el proveedor).
    if ruta_audio is None:
        base_audio = settings.audio_dir / f"resp_{uuid4().hex}"
        try:
            t0 = time.perf_counter()
            ruta_audio = await asyncio.to_thread(tts.sintetizar, texto_respuesta, base_audio)
            tiempos["tts_s"] = round(time.perf_counter() - t0, 2)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Falló el TTS")
            raise HTTPException(503, "No se pudo generar la voz de respuesta.") from exc

    tiempos["total_s"] = round(time.perf_counter() - inicio_total, 2)
    logger.info("Turno %s | tiempos: %s | habló %.0f s en total",
                sesion.id[:8], tiempos, sesion.segundos_usuario)

    return {
        "session_id": sesion.id,
        "texto_usuario": texto_usuario,
        "texto_respuesta": texto_respuesta,
        "audio_url": f"/audio/{ruta_audio.name}",
        "tiempos": tiempos,
        "tiempo_conversacion": _tiempo(sesion, limite_s),
        "limite_alcanzado": limite_alcanzado,
    }


@app.get("/conversar/{session_id}/tiempo")
async def tiempo_de_conversacion(
    session_id: str,
    usuario: Annotated[models.Usuario, Depends(requiere_rol(models.Rol.ADULTO_MAYOR))],
    db: Annotated[Session, Depends(get_db)],
):
    """Cuánto ha hablado la persona en esa sesión y cuánto le queda (para mostrar un contador)."""
    sesion = _obtener_o_crear_sesion(db, usuario, session_id)
    limite_s = _limite_segundos()
    agotado = (limite_s is not None and (sesion.segundos_usuario or 0.0) >= limite_s
               and not guardia.hay_senal_reciente(db, sesion.id))
    return {"session_id": sesion.id, **_tiempo(sesion, limite_s), "limite_alcanzado": agotado}


@app.get("/audio/{nombre}")
async def obtener_audio(nombre: str):
    """Sirve el audio generado (.mp3 de edge-tts o .wav de Piper).

    OJO: por ahora NO pide token; se protege con el nombre aleatorio (uuid) y con
    la limpieza automática (los audios de respuesta duran AUDIO_VIGENCIA_MIN
    minutos). `Path(nombre).name` evita rutas como ../../x.
    """
    ruta = settings.audio_dir / Path(nombre).name
    if not ruta.is_file():
        raise HTTPException(404, "Audio no encontrado")

    tipo = "audio/mpeg" if ruta.suffix == ".mp3" else "audio/wav"
    return FileResponse(ruta, media_type=tipo)