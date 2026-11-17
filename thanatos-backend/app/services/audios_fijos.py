"""
Audios que se repiten (guía del menú, introducciones de ejercicios, mensaje de
riesgo rojo). Se generan UNA vez y se reutilizan: así responden al instante y
suenan siempre igual. Si el texto cambia, se genera un audio nuevo.

Los archivos se llaman fijo_<clave>_<huella>.<ext> y viven en la carpeta de
audios, por lo que se sirven con el mismo endpoint /audio/<nombre>.
(Si algún día se limpia tmp_audio/, NO borrar los que empiezan con "fijo_".)
"""
import hashlib
import logging
from pathlib import Path

from app.config import settings
from app.services import tts

logger = logging.getLogger("thanatos.audios_fijos")


def obtener(clave: str, texto: str) -> Path:
    """Ruta del audio de `texto`. Función BLOQUEANTE (puede sintetizar)."""
    huella = hashlib.sha1(texto.encode("utf-8")).hexdigest()[:8]
    base = settings.audio_dir / f"fijo_{clave}_{huella}"
    for extension in (".mp3", ".wav"):
        candidato = base.with_suffix(extension)
        if candidato.is_file() and candidato.stat().st_size > 0:
            return candidato
    return tts.sintetizar(texto, base)


def precalentar(textos: dict[str, str]) -> None:
    """Genera de antemano varios audios ({clave: texto}). Los errores solo se registran."""
    for clave, texto in textos.items():
        try:
            obtener(clave, texto)
        except Exception:  # noqa: BLE001
            logger.exception("No se pudo precalentar el audio '%s'", clave)