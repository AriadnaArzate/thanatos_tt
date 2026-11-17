"""
Resumen de lo que el paciente ha hablado, para el tanatólogo.

El tanatólogo NO lee las conversaciones: recibe un resumen por temas. Para que el
resumen no sea una forma de leer la conversación, se revisa que NO reproduzca
frases de la persona: si comparte 6 palabras seguidas con lo que ella/el dijo, se le
pide al modelo que lo reformule, y si aun así copia, se descartan esas oraciones.
"""
import re
import unicodedata

from app.services import llm

_N = 6   # cuántas palabras seguidas iguales cuentan como una cita


def _palabras(texto: str) -> list[str]:
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    sin_marcas = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9]+", sin_marcas)


def _gramas(texto: str) -> set[tuple[str, ...]]:
    palabras = _palabras(texto)
    return {tuple(palabras[i:i + _N]) for i in range(len(palabras) - _N + 1)}


def _gramas_de_fuentes(fuentes: list[str]) -> set[tuple[str, ...]]:
    gramas: set[tuple[str, ...]] = set()
    for frase in fuentes:       # cada frase por separado, para no unir el final de una con el inicio de otra
        gramas |= _gramas(frase)
    return gramas


def copia_frases(resumen: str, fuentes: list[str]) -> bool:
    """True si el resumen reproduce al menos 6 palabras seguidas de lo que dijo la persona."""
    return bool(_gramas(resumen) & _gramas_de_fuentes(fuentes))


def _quitar_citas(resumen: str, fuentes: list[str]) -> str:
    """Conserva solo las oraciones del resumen que no copian a la persona."""
    gramas_fuente = _gramas_de_fuentes(fuentes)
    oraciones = re.split(r"(?<=[.!?])\s+", resumen.strip())
    return " ".join(o for o in oraciones if o and not (_gramas(o) & gramas_fuente))


async def resumir(frases: list[str]) -> str:
    """Resumen por temas de lo que la persona dijo, sin citas textuales."""
    texto = await llm.generar_resumen_paciente(frases)
    if copia_frases(texto, frases):
        texto = await llm.generar_resumen_paciente(frases, estricto=True)
    if copia_frases(texto, frases):
        texto = _quitar_citas(texto, frases)
    return texto or "No fue posible generar un resumen sin reproducir lo que dijo la persona."