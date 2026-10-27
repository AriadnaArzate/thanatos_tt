"""
Backend de Thanatos - versión mínima del CICLO DE VOZ.

    audio del adulto mayor
        -> Whisper (ASR)  : audio -> texto
        -> Ollama  (NLP)  : texto -> respuesta
        -> Piper   (TTS)  : respuesta -> audio

Todavía NO hay: login/roles, base de datos, clasificación de riesgo (RN-08),
alertas ni ejercicios. El objetivo de esta etapa es medir LATENCIA y calidad
del ciclo completo antes de construir lo demás.

Arranque:  uvicorn app.main:app --reload
Docs interactivas (para probar sin código): http://localhost:8000/docs
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import settings
from app.services import asr, llm, tts

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("thanatos.main")

# Se dice cuando Whisper no detecta habla (silencio, ruido, audio corto).
MENSAJE_NO_ENTENDI = "Disculpe, no alcancé a escucharle bien. ¿Podría repetirlo, por favor?"

# Historial por sesión, EN MEMORIA: se pierde al reiniciar el servidor.
# Se reemplazará por SQLite (sesiones por ID) en la siguiente etapa.
_historiales: dict[str, list[dict]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Se ejecuta al arrancar: prepara carpetas y calienta los modelos para que
    la primera conversación real no sea lenta."""
    settings.audio_dir.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(asr.precargar_modelo)
    if not await llm.ollama_disponible():
        logger.warning("Ollama NO responde en %s. Ábrelo y descarga el modelo: "
                       "ollama pull %s", settings.ollama_host, settings.ollama_model)
    if not Path(settings.piper_voice_path).exists():
        logger.warning("No se encontró la voz de Piper en '%s'.", settings.piper_voice_path)
    yield


app = FastAPI(title="Thanatos - motor conversacional", lifespan=lifespan)


@app.get("/salud")
async def salud():
    """Revisión rápida de que cada pieza está lista."""
    return {
        "whisper_cargado": asr._modelo is not None,  # noqa: SLF001
        "ollama": await llm.ollama_disponible(),
        "voz_piper": Path(settings.piper_voice_path).exists(),
    }


@app.post("/conversar")
async def conversar(
    audio: UploadFile = File(..., description="Audio del usuario (wav, m4a, mp3...)"),
    session_id: str | None = Form(None, description="Vacío en el primer turno"),
):
    """Un turno de conversación: recibe audio y devuelve texto + audio de respuesta.

    Devolvemos JSON (y el audio aparte, en /audio/...) porque así vemos los
    textos intermedios y los TIEMPOS de cada etapa, que es lo que queremos
    medir ahora.
    """
    tiempos: dict[str, float] = {}
    inicio_total = time.perf_counter()

    session_id = session_id or uuid4().hex
    historial = _historiales.setdefault(session_id, [])

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
        # No hubo habla reconocible: no llamamos al LLM ni ensuciamos el historial.
        texto_respuesta = MENSAJE_NO_ENTENDI
        tiempos["llm_s"] = 0.0
    else:
        historial.append({"role": "user", "content": texto_usuario})
        try:
            t0 = time.perf_counter()
            texto_respuesta = await llm.generar_respuesta(historial)
            tiempos["llm_s"] = round(time.perf_counter() - t0, 2)
        except Exception as exc:  # noqa: BLE001
            historial.pop()  # deshacemos el turno para poder reintentar
            logger.exception("Falló Ollama")
            raise HTTPException(503, "El motor conversacional no está disponible.") from exc
        historial.append({"role": "assistant", "content": texto_respuesta})
        # Ventana deslizante: solo recordamos los últimos N turnos (2 mensajes c/u).
        del historial[: -settings.max_history_turns * 2]

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
    logger.info("Turno %s | tiempos: %s", session_id[:8], tiempos)

    return {
        "session_id": session_id,
        "texto_usuario": texto_usuario,
        "texto_respuesta": texto_respuesta,
        "audio_url": f"/audio/{ruta_audio.name}",
        "tiempos": tiempos,
    }


@app.get("/audio/{nombre}")
async def obtener_audio(nombre: str):
    """Sirve el audio generado (.mp3 de edge-tts o .wav de Piper).
    `Path(nombre).name` evita que alguien pida rutas como ../../algo para
    leer archivos fuera de la carpeta de audios."""
    ruta = settings.audio_dir / Path(nombre).name
    if not ruta.is_file():
        raise HTTPException(404, "Audio no encontrado")

    tipo = "audio/mpeg" if ruta.suffix == ".mp3" else "audio/wav"
    return FileResponse(ruta, media_type=tipo)

# TODO: los audios de respuesta se acumulan en tmp_audio/. Falta una limpieza
# periódica (o borrarlos tras la descarga).