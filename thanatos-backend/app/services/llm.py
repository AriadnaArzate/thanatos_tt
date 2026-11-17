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
        'No uses "tú", "tu", "te" ni "ti". Conserva el sentido, el mismo número de oraciones '
        "y la misma longitud; no agregues ideas nuevas. Responde SOLO con el texto reescrito, "
        "sin comillas ni explicaciones.\n\n"
        f"Texto: {texto}"
    )
    respuesta = await _cliente.chat(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": instruccion}],
        options={"temperature": 0.2, "num_predict": settings.ollama_max_tokens},
        keep_alive=settings.ollama_keep_alive,
    )
    return _recortar_a_oracion_completa(respuesta["message"]["content"])


async def generar_respuesta(
    historial: list[dict], ejemplos_texto: str = "", extra_sistema: str = ""
) -> str:
    """Genera la siguiente respuesta del acompañante.

    `historial`: mensajes previos en formato de chat
        [{"role": "user", "content": "..."}, {"role": "assistant", ...}, ...]
    `ejemplos_texto`: ejemplos de estilo del dataset semilla (puede ir vacío).
    `extra_sistema`: instrucciones adicionales (las de un ejercicio, o la nota de
        riesgo amarillo). Puede ir vacío.
    El prompt de sistema se arma aquí; NO se guarda en el historial.
    """
    partes = [SYSTEM_PROMPT, extra_sistema, ejemplos_texto]
    sistema = "\n\n".join(p for p in partes if p)
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


async def generar_narracion(frases: list[str]) -> str:
    """Organiza lo que la persona dijo (Legado emocional) en un relato breve, en
    primera persona. Riesgo: un modelo pequeño puede inventar detalles; por eso
    la instrucción es usar SOLO lo dicho y la persona debe escucharlo y confirmarlo
    antes de guardarlo."""
    lista = "\n".join(f"- {f}" for f in frases)
    instruccion = (
        "A continuación hay frases que una persona adulta mayor dijo sobre sus recuerdos y "
        "enseñanzas. Escribe un relato breve (máximo 120 palabras), en primera persona, con las "
        "palabras y los datos de la persona. Usa SOLO lo que dijo: no agregues nombres, fechas, "
        "lugares ni hechos nuevos. Si dijo poco, el relato debe ser corto. Español de México, "
        "sencillo y cálido. Responde SOLO con el relato.\n\n"
        f"Frases:\n{lista}"
    )
    respuesta = await _cliente.chat(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": instruccion}],
        options={"temperature": 0.3, "num_predict": 350},
        keep_alive=settings.ollama_keep_alive,
    )
    return _recortar_a_oracion_completa(respuesta["message"]["content"])

def _ultimas_frases(frases: list[str], max_caracteres: int = 6000) -> list[str]:
    """Las frases más recientes que caben en `max_caracteres`, en orden cronológico
    (un modelo pequeño no puede leer conversaciones muy largas)."""
    elegidas: list[str] = []
    total = 0
    for frase in reversed(frases):
        if total + len(frase) > max_caracteres and elegidas:
            break
        elegidas.append(frase)
        total += len(frase)
    return list(reversed(elegidas))


async def generar_resumen_paciente(frases: list[str], estricto: bool = False) -> str:
    """Resumen por temas de lo que un paciente dijo, para el tanatólogo. Debe ser
    una paráfrasis: sin citas, sin diagnósticos y sin datos que la persona no dijo."""
    lista = "\n".join(f"- {f}" for f in _ultimas_frases(frases))
    instruccion = (
        "Eres un asistente que prepara un resumen para un tanatólogo. A continuación están las "
        "frases que un paciente adulto mayor dijo en sus conversaciones con una aplicación de "
        "acompañamiento en el duelo. Escribe un resumen de 3 a 5 oraciones, en tercera persona "
        '("la persona..."), con los temas de los que habló, las emociones que expresó y las '
        "personas o pérdidas que mencionó. Reglas: usa SOLO lo que dijo, no agregues datos, no "
        "diagnostiques y no interpretes más allá de lo dicho. NO copies ni cites frases "
        'textuales: parafrasea. No uses nombres propios (di "su esposo", "su hija"). Si hay poco '
        "contenido, dilo en una oración. Responde SOLO con el resumen."
    )
    if estricto:
        instruccion += (
            " IMPORTANTE: tu resumen anterior copió frases textuales. Reescríbelo con palabras "
            "distintas, sin reproducir ninguna frase de la persona."
        )
    respuesta = await _cliente.chat(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": f"{instruccion}\n\nFrases:\n{lista}"}],
        options={"temperature": 0.2, "num_predict": 300},
        keep_alive=settings.ollama_keep_alive,
    )
    return _recortar_a_oracion_completa(respuesta["message"]["content"])

async def explicar_ejercicio(
    nombre: str, objetivo: str, pasos: tuple[str, ...], duracion: str, emocion: str | None = None
) -> str:
    """Explica POR VOZ un ejercicio de desahogo para que la persona lo haga por su cuenta.

    El modelo solo puede usar los pasos indicados. Si la explicación sale tuteando o demasiado
    corta, lanza ValueError y quien la llama usa el texto de respaldo del ejercicio.
    """
    lista = "\n".join(f"{i}. {p}" for i, p in enumerate(pasos, start=1))
    contexto = (
        f"La persona indicó que hoy se siente {emocion}. Comience con una frase breve y cálida que "
        "lo reconozca, sin decir que lo registró en la aplicación. "
        if emocion else ""
    )
    instruccion = (
        "Eres Thanatos, un acompañante de apoyo en el duelo para personas adultas mayores de México. "
        "Vas a EXPLICAR POR VOZ cómo hacer, por su cuenta y fuera de la aplicación, el ejercicio que "
        "se describe abajo. Trata a la persona de USTED (le, su, usted); no uses tú, tu ni te. Usa de "
        "4 a 7 oraciones cortas y sencillas, sin listas, sin emojis y sin palabras técnicas. Menciona "
        "el nombre del ejercicio, qué se busca, los pasos en orden y cuánto tiempo puede tomar. Usa "
        "SOLO los pasos indicados: no agregues pasos, no prometas resultados ni des consejos médicos. "
        f"{contexto}Responde SOLO con la explicación.\n\n"
        f"Ejercicio: {nombre}\nObjetivo: {objetivo}\nPasos:\n{lista}\nDuración: {duracion}"
    )
    respuesta = await _cliente.chat(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": instruccion}],
        options={"temperature": 0.4, "num_predict": 280},
        keep_alive=settings.ollama_keep_alive,
    )
    texto = _recortar_a_oracion_completa(respuesta["message"]["content"])
    if tiene_tuteo(texto):
        raise ValueError("La explicación del modelo usó trato de tú.")
    if len(texto.split()) < 30:
        raise ValueError("La explicación del modelo quedó demasiado corta.")
    return texto