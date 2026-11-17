"""
Contexto emocional: la emoción que la persona registra en "Registrar emoción"
alimenta al motor conversacional. Si registró una emoción hace poco, se le avisa
al modelo (sin decírselo a la persona) para que responda con ese tono.

El catálogo sigue la cuadrícula de 2 columnas por 3 filas de la app, en este orden
(de izquierda a derecha y de arriba abajo). [VALIDAR los nombres con la tanatóloga]
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import RegistroEmocion

# id: lo que guarda la base | etiqueta: lo que ve la persona | para_el_modelo: cómo se le dice al modelo.
CATALOGO_EMOCIONES = [
    {"id": "tristeza", "etiqueta": "Tristeza", "para_el_modelo": "tristeza"},
    {"id": "ira_frustracion", "etiqueta": "Ira/Frustración", "para_el_modelo": "ira o frustración"},
    {"id": "frustracion", "etiqueta": "Frustración", "para_el_modelo": "frustración"},
    {"id": "calma", "etiqueta": "Calma", "para_el_modelo": "calma"},
    {"id": "ansiedad_miedo", "etiqueta": "Ansiedad/Miedo", "para_el_modelo": "ansiedad o miedo"},
    {"id": "soledad_vacio", "etiqueta": "Soledad/Vacío", "para_el_modelo": "soledad o vacío"},
]
_POR_ID = {e["id"]: e for e in CATALOGO_EMOCIONES}


def ids_validos() -> set[str]:
    return set(_POR_ID)


def para_el_modelo(emocion_id: str) -> str:
    """Cómo nombrar la emoción ante el modelo (tolera ids de versiones anteriores del catálogo)."""
    entrada = _POR_ID.get(emocion_id)
    return entrada["para_el_modelo"] if entrada else emocion_id.replace("_", " ")


def emocion_reciente(db: Session, usuario_id: int) -> RegistroEmocion | None:
    """La última emoción que la persona registró dentro de las últimas HORAS_VIGENCIA_EMOCION horas."""
    desde = datetime.now(timezone.utc) - timedelta(hours=settings.horas_vigencia_emocion)
    return db.scalar(
        select(RegistroEmocion)
        .where(RegistroEmocion.usuario_id == usuario_id, RegistroEmocion.creado_en >= desde)
        .order_by(RegistroEmocion.id.desc())
        .limit(1)
    )


def nota_emocional(db: Session, usuario_id: int) -> str:
    """Instrucción para el modelo con la emoción reciente de la persona ("" si no hay)."""
    registro = emocion_reciente(db, usuario_id)
    if registro is None:
        return ""
    return (
        f"CONTEXTO: hoy la persona indicó en la aplicación que se siente {para_el_modelo(registro.emocion)}. "
        "Téngalo en cuenta con delicadeza, sin decirle que lo registró ni repetirlo de forma mecánica. "
        "Si lo que dice ahora no coincide con esa emoción, haga caso a lo que dice ahora."
    )