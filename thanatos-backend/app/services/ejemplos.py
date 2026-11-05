"""
Ejemplos de estilo a partir del dataset semilla (SIN fine-tuning).

Idea: en cada turno se buscan los K ejemplos del dataset cuyo mensaje se parezca
más a lo que dijo la persona, y se muestran al LLM dentro del prompt como
referencia de tono, longitud y trato de "usted". El modelo no se reentrena.

VALIDACIÓN: se usan las filas cuyo estado_validacion esté en
EJEMPLOS_ESTADOS_PERMITIDOS (por defecto "aprobada" y "pendiente": la tanatóloga
revisó una MUESTRA del dataset y lo consideró correcto; ver
data/registro_validacion.md). Las filas "corregir" y "rechazada" NUNCA se usan.

TRAZABILIDAD: cada Ejemplo conserva su id, intención y marco conceptual para
poder registrar qué ejemplos influyeron en cada respuesta.
"""
import logging
import math
import re
from dataclasses import dataclass
from pathlib import Path

import openpyxl
from ollama import AsyncClient

from app.config import settings

logger = logging.getLogger("thanatos.ejemplos")

_cliente = AsyncClient(host=settings.ollama_host)

# Columnas que debe tener la hoja "Dataset_empatico". Si alguien cambia el
# formato del Excel, preferimos fallar con un mensaje claro y no en silencio.
_COLUMNAS = {"id", "intencion", "emocion_principal", "marco_conceptual",
             "fuente_base", "mensaje_usuario", "respuesta_candidata", "estado_validacion"}


@dataclass(frozen=True)
class Ejemplo:
    id: str
    intencion: str
    emocion: str
    marco: str
    fuente: str
    mensaje: str
    respuesta: str


# Índice en memoria: se llena una vez al arrancar (ver cargar_indice).
_ejemplos: list[Ejemplo] = []
_vectores: list[list[float]] = []


def _leer_dataset() -> list[Ejemplo]:
    """Lee el Excel y devuelve solo las filas permitidas según su validación."""
    ruta = Path(settings.dataset_path)
    if not ruta.is_file():
        logger.warning("No se encontró el dataset en '%s'. Se continúa sin ejemplos.", ruta)
        return []

    libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    try:
        filas = libro["Dataset_empatico"].iter_rows(values_only=True)
        encabezado = [str(c).strip() if c is not None else "" for c in next(filas)]
        idx = {nombre: i for i, nombre in enumerate(encabezado)}
        faltan = _COLUMNAS - idx.keys()
        if faltan:
            raise RuntimeError(f"Al dataset le faltan columnas: {sorted(faltan)}")

        # "corregir" y "rechazada" se excluyen siempre, aunque alguien las ponga en el .env.
        permitidos = {e.strip().lower() for e in settings.ejemplos_estados_permitidos.split(",")}
        permitidos -= {"corregir", "rechazada"}

        def celda(fila, nombre) -> str:
            valor = fila[idx[nombre]]
            return "" if valor is None else str(valor).strip()

        ejemplos = []
        for fila in filas:
            if not fila or not celda(fila, "id"):
                continue
            if celda(fila, "estado_validacion").lower() not in permitidos:
                continue
            ejemplos.append(Ejemplo(
                id=celda(fila, "id"), intencion=celda(fila, "intencion"),
                emocion=celda(fila, "emocion_principal"), marco=celda(fila, "marco_conceptual"),
                fuente=celda(fila, "fuente_base"), mensaje=celda(fila, "mensaje_usuario"),
                respuesta=celda(fila, "respuesta_candidata"),
            ))
        return ejemplos
    finally:
        libro.close()


async def _embeber(textos: list[str]) -> list[list[float]]:
    """Convierte textos en vectores con un modelo de embeddings de Ollama."""
    respuesta = await _cliente.embed(
        model=settings.embedding_model, input=textos, keep_alive=settings.ollama_keep_alive
    )
    return [list(v) for v in respuesta["embeddings"]]


def _normalizar(vector: list[float]) -> list[float]:
    """Vector de largo 1: así el producto punto equivale a la similitud coseno."""
    norma = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [x / norma for x in vector]


async def cargar_indice() -> None:
    """Se llama al arrancar el servidor. Nunca debe tumbarlo: si algo falla,
    el motor sigue funcionando, solo que sin ejemplos."""
    global _ejemplos, _vectores
    if not settings.ejemplos_activos:
        logger.info("Ejemplos de estilo desactivados (EJEMPLOS_ACTIVOS=false).")
        return

    candidatos = _leer_dataset()
    if not candidatos:
        logger.warning("0 ejemplos disponibles: ninguna fila tiene un estado permitido (%s).",
                       settings.ejemplos_estados_permitidos)
        return

    try:
        vectores = await _embeber([e.mensaje for e in candidatos])
    except Exception:  # noqa: BLE001
        logger.exception("No se pudieron calcular los embeddings. ¿Ejecutaste 'ollama pull %s'? "
                         "Se continúa sin ejemplos.", settings.embedding_model)
        return

    _ejemplos = candidatos
    _vectores = [_normalizar(v) for v in vectores]
    logger.info("Ejemplos de estilo cargados: %d (estados permitidos: %s)",
                len(_ejemplos), settings.ejemplos_estados_permitidos)

def _dividir_en_oraciones(texto: str) -> list[str]:
    """Parte el texto en oraciones (máximo 8, ignorando fragmentos muy cortos).
    Sirve porque una persona puede hablar de varios temas en un solo audio."""
    partes = [p.strip() for p in re.split(r"(?<=[.!?])\s+", texto) if len(p.strip()) > 15]
    return partes[:8]


async def buscar(texto: str, k: int | None = None) -> list[Ejemplo]:
    """Los K ejemplos más parecidos a lo que dijo la persona.

    Un audio largo mezcla varios temas y, comparado entero contra ejemplos que
    tratan un solo tema, el parecido se diluye. Por eso se compara el texto
    completo Y cada oración por separado, y cada ejemplo se queda con su MEJOR
    parecido. Si no hay índice o algo falla, devuelve una lista vacía.
    """
    if not _ejemplos or not texto.strip():
        return []

    consultas = [texto.strip()]
    consultas += [o for o in _dividir_en_oraciones(texto) if o not in consultas]
    try:
        vectores_consulta = [_normalizar(v) for v in await _embeber(consultas)]
    except Exception:  # noqa: BLE001
        logger.exception("Falló el embedding de la consulta; se responde sin ejemplos.")
        return []

    puntajes = []
    for vector, ejemplo in zip(_vectores, _ejemplos):
        mejor = max(sum(a * b for a, b in zip(q, vector)) for q in vectores_consulta)
        puntajes.append((mejor, ejemplo))
    puntajes.sort(key=lambda par: par[0], reverse=True)
    return [e for _, e in puntajes[: k or settings.ejemplos_k]]


def formatear_para_prompt(ejemplos: list[Ejemplo]) -> str:
    """Texto que se añade al prompt de sistema. Vacío si no hay ejemplos."""
    if not ejemplos:
        return ""
    bloques = [f'Persona: "{e.mensaje}"\nRespuesta: "{e.respuesta}"' for e in ejemplos]
    return (
        "EJEMPLOS DE ESTILO (solo como referencia de tono, longitud y trato de usted; NO los "
        "copies ni repitas sus frases, y responde a lo que la persona dijo ahora):\n\n"
        + "\n\n".join(bloques)
    )