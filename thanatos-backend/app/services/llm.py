"""
Capa de NLP: genera la respuesta conversacional con Ollama (LLM local).

Requiere que el servidor de Ollama esté corriendo (la app de escritorio de
Ollama lo levanta sola en http://localhost:11434) y que el modelo esté
descargado: `ollama pull llama3.2:3b`.
"""
import logging

from ollama import AsyncClient

from app.config import settings
from app.services.prompts.system_prompt import SYSTEM_PROMPT

logger = logging.getLogger("thanatos.llm")

_cliente = AsyncClient(host=settings.ollama_host)


async def ollama_disponible() -> bool:
    """True si el servidor de Ollama responde. Se usa en el arranque y en /salud."""
    try:
        await _cliente.list()
        return True
    except Exception:  # noqa: BLE001 - cualquier fallo significa "no disponible"
        return False


def _recortar_a_oracion_completa(texto: str) -> str:
    """Si el modelo se cortó por el tope de tokens a media frase, descarta la
    frase incompleta para que la voz no termine a la mitad de una palabra."""
    texto = texto.strip()
    if not texto or texto[-1] in ".?!…":
        return texto
    fin = max(texto.rfind("."), texto.rfind("?"), texto.rfind("!"))
    return texto[: fin + 1] if fin != -1 else texto


async def generar_respuesta(historial: list[dict]) -> str:
    """Genera la siguiente respuesta del acompañante.

    `historial` es la lista de mensajes previos con el formato de chat:
        [{"role": "user", "content": "..."}, {"role": "assistant", ...}, ...]
    El prompt de sistema se antepone aquí; NO se guarda en el historial.
    """
    mensajes = [{"role": "system", "content": SYSTEM_PROMPT}, *historial]
    respuesta = await _cliente.chat(
        model=settings.ollama_model,
        messages=mensajes,
        options={
            "temperature": settings.ollama_temperature,
            "num_predict": settings.ollama_max_tokens,
        },
        keep_alive=settings.ollama_keep_alive,
    )
    texto = respuesta["message"]["content"]
    return _recortar_a_oracion_completa(texto)