"""
Capa de NLP: genera la respuesta conversacional con Ollama (LLM local).

Requiere que el servidor de Ollama esté corriendo (la app de escritorio de
Ollama lo levanta sola en http://localhost:11434) y que el modelo esté
descargado: `ollama pull llama3.2:3b`.

REGISTRO: el trato debe ser siempre de "usted" (validado en el dataset). Los
modelos pequeños a veces se pasan a "tú" aunque el prompt lo prohíba, así que
cada respuesta se REVISA y, si trae tuteo, se reescribe en "usted".
"""
import logging
import re

from ollama import AsyncClient

from app.config import settings
from app.services.prompts.system_prompt import SYSTEM_PROMPT

logger = logging.getLogger("thanatos.llm")

_cliente = AsyncClient(host=settings.ollama_host)

# Formas que solo existen en trato de "tú". Se omiten a propósito verbos como
# "recuerda" o "piensa", que también son correctos en "usted" ("le recuerda").
# Es una lista curada: atrapa lo más común, no es un detector perfecto.
_TUTEO = re.compile(
    r"\b(tú|tu|tus|ti|te|contigo|hayas|tengas|puedas|quieras|sientas|necesites|"
    r"tienes|puedes|quieres|sientes|necesitas|eres|estás|has|sabes|haces|piensas|"
    r"crees|debes|vives|recuerdas|dime|cuéntame|permítete)\b",
    re.IGNORECASE,
)


def tiene_tuteo(texto: str) -> bool:
    """True si el texto contiene alguna forma de trato de "tú"."""
    return bool(_TUTEO.search(texto))


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


async def _reescribir_en_usted(texto: str) -> str:
    """Pide al modelo que reescriba `texto` en "usted". Reescribir es una tarea
    más fácil para un modelo pequeño que generar respetando una regla de estilo."""
    instruccion = (
        'Reescribe el siguiente texto tratando a la persona de "usted": usa le, su, usted y '
        'verbos en tercera persona (por ejemplo "haya", "tenga", "puede", "le recuerda"). '
        'No uses "tú", "tu", "te" ni "ti". Conserva el sentido y la longitud. Responde SOLO '
        "con el texto reescrito, sin comillas ni explicaciones.\n\n"
        f"Texto: {texto}"
    )
    respuesta = await _cliente.chat(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": instruccion}],
        options={"temperature": 0.2, "num_predict": settings.ollama_max_tokens},
        keep_alive=settings.ollama_keep_alive,
    )
    return _recortar_a_oracion_completa(respuesta["message"]["content"])


async def generar_respuesta(historial: list[dict], ejemplos_texto: str = "") -> str:
    """Genera la siguiente respuesta del acompañante.

    `historial` es la lista de mensajes previos con el formato de chat:
        [{"role": "user", "content": "..."}, {"role": "assistant", ...}, ...]
    `ejemplos_texto` son los ejemplos de estilo del dataset semilla (puede ir
    vacío). El prompt de sistema se arma aquí; NO se guarda en el historial.
    """
    sistema = f"{SYSTEM_PROMPT}\n{ejemplos_texto}" if ejemplos_texto else SYSTEM_PROMPT
    mensajes = [{"role": "system", "content": sistema}, *historial]
    respuesta = await _cliente.chat(
        model=settings.ollama_model,
        messages=mensajes,
        options={
            "temperature": settings.ollama_temperature,
            "num_predict": settings.ollama_max_tokens,
        },
        keep_alive=settings.ollama_keep_alive,
    )
    texto = _recortar_a_oracion_completa(respuesta["message"]["content"])

    # Revisión de registro: si hay tuteo, un intento de reescritura en "usted".
    if tiene_tuteo(texto):
        logger.warning("Respuesta con tuteo; se reescribe en 'usted'.")
        reescrito = await _reescribir_en_usted(texto)
        if reescrito:
            texto = reescrito
        if tiene_tuteo(texto):
            logger.warning("La reescritura aún contiene tuteo; se entrega de todos modos.")
    return texto