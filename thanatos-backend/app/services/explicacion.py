"""
Explicación del semáforo para el tanatólogo.

Es DETERMINISTA: se arma con las señales que el módulo de riesgo registró (nivel,
categorías, fechas), sin pasar por un modelo de lenguaje. Así lo que se le explica
al tanatólogo es exactamente lo que provocó el color, y se puede rastrear. Un
modelo de lenguaje podría redactar una justificación que suene bien pero no
corresponda a lo que realmente se detectó.

Nunca incluye frases de la persona: solo categorías ("expresó soledad"), conteos y fechas.
"""
from collections import Counter
from datetime import datetime, timedelta, timezone

from app.services.riesgo import ORDEN, REGLAS_VERSION, etiqueta

# Ciudad de México (UTC-6, sin horario de verano). La base guarda las fechas en UTC.
_ZONA = timezone(timedelta(hours=-6))
_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
          "septiembre", "octubre", "noviembre", "diciembre"]


def _fecha(momento: datetime) -> str:
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    local = momento.astimezone(_ZONA)
    return f"{local.day} de {_MESES[local.month - 1]}"


def _unir(elementos: list[str]) -> str:
    """['a', 'b', 'c'] -> 'a, b y c'"""
    if len(elementos) <= 1:
        return "".join(elementos)
    return ", ".join(elementos[:-1]) + " y " + elementos[-1]


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def _categorias(senal) -> list[str]:
    return [c.strip() for c in senal.categorias.split(",") if c.strip()]


def nivel_maximo(senales) -> str:
    """El nivel más alto entre las señales (verde si no hay ninguna)."""
    return max((s.nivel for s in senales), key=lambda n: ORDEN.get(n, 0), default="verde")


def motivo_corto(senales) -> str:
    """Una línea para la tarjeta del paciente: qué se detectó en el nivel más alto."""
    nivel = nivel_maximo(senales)
    if nivel == "verde":
        return ""
    conteo = Counter(c for s in senales if s.nivel == nivel for c in _categorias(s))
    return _unir([etiqueta(c) for c, _ in conteo.most_common(3)]).capitalize()


def explicar(senales, previas: int, dias: int, alertas_abiertas: int) -> dict:
    """Arma el semáforo y su razonamiento.

    senales          señales del periodo (objetos con nivel, categorias y creado_en)
    previas          cuántas señales hubo en el periodo anterior de la misma duración
    alertas_abiertas alertas de este paciente que el tanatólogo aún no marca como atendidas
    """
    semaforo = nivel_maximo(senales)
    como_se_calculo = (
        f"Se toma el nivel más alto detectado en los últimos {dias} días. Lo asignan reglas "
        f"fijas (versión {REGLAS_VERSION}) aplicadas a lo que la persona dijo; no es la "
        "opinión de un modelo de lenguaje."
    )

    if not senales:
        return {
            "semaforo": "verde",
            "razonamiento": f"Verde: no se detectaron señales de riesgo en los últimos {dias} días.",
            "como_se_calculo": como_se_calculo,
            "detalle": [], "tendencia": "sin_senales" if previas == 0 else "disminuye",
            "alertas_abiertas": alertas_abiertas,
        }

    por_nivel = Counter(s.nivel for s in senales)
    partes = [
        f"{_plural(por_nivel[n], 'señal', 'señales')} de nivel {n}"
        for n in ("rojo", "amarillo") if por_nivel[n]
    ]

    # Detalle por categoría: cuántas veces, en qué nivel y cuándo fue la última.
    veces: Counter = Counter()
    nivel_cat: dict[str, str] = {}
    ultima: dict[str, datetime] = {}
    for s in senales:
        for c in _categorias(s):
            veces[c] += 1
            if ORDEN.get(s.nivel, 0) >= ORDEN.get(nivel_cat.get(c, "verde"), 0):
                nivel_cat[c] = s.nivel
            if c not in ultima or s.creado_en > ultima[c]:
                ultima[c] = s.creado_en
    detalle = [
        {"categoria": c, "descripcion": etiqueta(c), "nivel": nivel_cat[c], "veces": n,
         "ultima": ultima[c]}
        for c, n in sorted(veces.items(), key=lambda kv: (-ORDEN[nivel_cat[kv[0]]], -kv[1]))
    ]

    # Se arma aparte (y no dentro de la f-string) para que sea válido en Python 3.10.
    que_hizo = _unir([
        d["descripcion"] + " (" + _plural(d["veces"], "vez", "veces") + ")" for d in detalle
    ])
    texto = (
        f"{semaforo.capitalize()}: en los últimos {dias} días se detectaron {_unir(partes)}. "
        f"La persona {que_hizo}. "
        f"La más reciente fue el {_fecha(max(s.creado_en for s in senales))}."
    )

    if len(senales) > previas:
        tendencia = "aumenta" if previas else "nuevo"
    elif len(senales) < previas:
        tendencia = "disminuye"
    else:
        tendencia = "igual"
    comparacion = {
        "aumenta": f"Hay más señales que en el periodo anterior ({len(senales)} frente a {previas}).",
        "nuevo": "En el periodo anterior no había señales.",
        "disminuye": f"Hay menos señales que en el periodo anterior ({len(senales)} frente a {previas}).",
        "igual": f"Hay la misma cantidad de señales que en el periodo anterior ({previas}).",
    }[tendencia]
    atencion = (
        f"Hay {_plural(alertas_abiertas, 'alerta sin atender', 'alertas sin atender')}."
        if alertas_abiertas else "Todas las alertas de esta persona están atendidas."
    )

    # En rojo no se narra la comparación: "hay menos señales" podría leerse como tranquilizador.
    if semaforo == "rojo":
        comparacion = ""
    razonamiento = " ".join(parte for parte in (texto, comparacion, atencion) if parte)

    return {
        "semaforo": semaforo,
        "razonamiento": razonamiento,
        "como_se_calculo": como_se_calculo,
        "detalle": detalle, "tendencia": tendencia, "alertas_abiertas": alertas_abiertas,
    }