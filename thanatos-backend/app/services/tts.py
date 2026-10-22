"""
Capa de TTS: texto -> voz.

Principal: edge-tts (voces neuronales de Microsoft Edge; gratis, sin cuenta,
requiere internet). NO es una API oficial: puede cambiar sin aviso.

PRIVACIDAD: a Microsoft solo viaja el TEXTO DE LA RESPUESTA del acompañante,
nunca el audio ni las palabras del usuario. 


Formato: edge-tts genera MP3 y Piper genera WAV, por eso `sintetizar` recibe
una ruta SIN extensión y devuelve la ruta final con la extensión correcta.
"""
import asyncio
import logging
import subprocess
import sys
from pathlib import Path

import edge_tts

from app.config import settings

logger = logging.getLogger("thanatos.tts")


def _sintetizar_edge(texto: str, base: Path) -> Path:
    salida = base.with_suffix(".mp3")
    comunicador = edge_tts.Communicate(
        texto, voice=settings.edge_voz, rate=settings.edge_velocidad
    )
    # edge-tts es async; como esta función corre en un hilo aparte
    # (asyncio.to_thread), podemos usar asyncio.run sin chocar con el servidor.
    asyncio.run(comunicador.save(str(salida)))
    if not salida.exists() or salida.stat().st_size == 0:
        raise RuntimeError("edge-tts no generó audio")
    return salida


def _sintetizar_piper(texto: str, base: Path) -> Path:
    """Piper como proceso externo (línea de comandos); el texto entra por stdin."""
    salida = base.with_suffix(".wav")
    cmd_base = [settings.piper_cmd] if settings.piper_cmd else [sys.executable, "-m", "piper"]
    comando = cmd_base + ["-m", settings.piper_voice_path, "-f", str(salida)]
    resultado = subprocess.run(
        comando, input=texto, text=True, encoding="utf-8", capture_output=True
    )
    if resultado.returncode != 0 or not salida.exists():
        raise RuntimeError(f"Piper falló: {resultado.stderr.strip()}")
    return salida


def sintetizar(texto: str, base: Path) -> Path:
    """Convierte `texto` a audio. `base` es la ruta SIN extensión; devuelve la
    ruta real (.mp3 o .wav). Función BLOQUEANTE: se llama con asyncio.to_thread."""
    if settings.tts_proveedor == "edge":
        try:
            return _sintetizar_edge(texto, base)
        except Exception:  # noqa: BLE001
            logger.exception("edge-tts falló")
            if not Path(settings.piper_voice_path).exists():
                raise  # no hay respaldo disponible
            logger.warning("Usando Piper como respaldo.")
    return _sintetizar_piper(texto, base)
