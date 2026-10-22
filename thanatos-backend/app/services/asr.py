"""
Capa de ASR: voz -> texto con Whisper.
Usamos `faster-whisper`, una implementación de Whisper (mismo modelo de OpenAI)
optimizada para CPU. Sigue siendo "Whisper" para efectos del diagrama de
arquitectura aprobado. Whisper SOLO transcribe: la voz de salida la genera Piper.

Ventaja práctica: decodifica m4a/mp3/wav/etc. por su cuenta.
"""
import logging
import re
from pathlib import Path

from faster_whisper import WhisperModel

from app.config import settings

logger = logging.getLogger("thanatos.asr")

# El modelo se carga UNA vez y se reutiliza (cargarlo tarda varios segundos).
_modelo: WhisperModel | None = None


def precargar_modelo() -> WhisperModel:
    """Carga Whisper en memoria. Se llama al arrancar el servidor para que la
    primera petición real no pague el costo de carga. La primera vez descarga
    el modelo de internet."""
    global _modelo
    if _modelo is None:
        logger.info("Cargando Whisper '%s' (%s, %s)...",
                    settings.whisper_model, settings.whisper_device,
                    settings.whisper_compute_type)
        _modelo = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    return _modelo


# --------------------------------------------------------------------------
# Corrección lingüística (objetivo de TT-1): NORMALIZAR el habla senescente.
# Esta versión es un BORRADOR mínimo; el módulo real se diseñará aparte.
# --------------------------------------------------------------------------
_MULETILLAS = re.compile(r"\b(?:e+h+|e+m+|m{2,}|h+m+)\b", re.IGNORECASE)
_PALABRA_REPETIDA = re.compile(r"\b(\w+)(?:\s+\1\b)+", re.IGNORECASE)


def limpiar_transcripcion(texto: str) -> str:
    """Quita muletillas y colapsa repeticiones inmediatas ("sí sí sí" -> "sí")
    antes de mandar el texto al LLM. Ojo: una repetición puede ser énfasis
    emocional; a validar si conviene conservarla."""
    texto = _MULETILLAS.sub("", texto)
    texto = _PALABRA_REPETIDA.sub(r"\1", texto)
    return re.sub(r"\s+", " ", texto).strip()


def transcribir(ruta_audio: Path) -> str:
    """Transcribe un archivo de audio a texto en español.

    Es una función BLOQUEANTE (usa CPU un rato). Desde código async se llama
    con `asyncio.to_thread(...)` para no congelar el servidor.
    """
    modelo = precargar_modelo()
    segmentos, _info = modelo.transcribe(
        str(ruta_audio),
        language="es",       # fijamos idioma: evita detecciones erróneas
        beam_size=5,
        vad_filter=True,     # ignora silencios largos (útil con pausas al hablar)
        vad_parameters={"min_silence_duration_ms": 1000},
        # Pista de contexto: ayuda a Whisper con el registro y el vocabulario.
        initial_prompt="Conversación en español de México con una persona adulta mayor.",
    )
    # `segmentos` es un generador: la transcripción ocurre al recorrerlo.
    texto = " ".join(seg.text.strip() for seg in segmentos)
    return limpiar_transcripcion(texto)