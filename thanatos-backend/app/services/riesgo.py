"""
Módulo de riesgo, versión 1.0: clasifica lo que dice la persona en verde,
amarillo o rojo.

  VERDE    sin señales: la conversación sigue normal.
  AMARILLO señales de malestar importante: el modelo responde con especial
           cuidado y se crea una alerta para el tanatólogo.
  ROJO     deseo de morir o de hacerse daño, dicho en primera persona: el modelo
           NO interviene; se responde con un texto fijo y se alerta al tanatólogo.

Cómo funciona: el texto se normaliza (minúsculas, sin acentos) y se compara con
patrones agrupados por categoría. Reglas de diseño:
  * Ante la duda se SUBE de nivel: es preferible una falsa alarma a una omisión.
  * "No quiero morir" NO es rojo (se descartan las negaciones).
  * Hablar de un tercero ("mi esposo quería morirse") no es rojo.
  * "Quiero morir en mi casa" (preferencia sobre el final de la vida) es amarillo,
    no rojo, para no mandar un mensaje de crisis a quien expresa algo habitual.

Cómo se comprueba: `python scripts/probar_riesgo.py` corre los casos de
data/casos_riesgo.csv. Para ampliar o corregir las reglas, se agregan casos ahí
y se ajusta este archivo hasta que todos pasen.

ESTADO DE VALIDACIÓN: las frases, las categorías y los textos de este módulo los
definió el desarrollador a partir de expresiones frecuentes; NO hay todavía una
validación formal de la tanatóloga. Se registra en data/registro_validacion_riesgo.md.

LÍMITES: es una lista de patrones. No entiende contexto, ironía ni frases que no
prevé, y puede fallar con errores de transcripción. No sustituye un protocolo
humano de respaldo.
"""
import re
import unicodedata
from dataclasses import dataclass, field

from app.config import settings

REGLAS_VERSION = "1.0"

ORDEN = {"verde": 0, "amarillo": 1, "rojo": 2}

# --- Piezas reutilizables (los patrones van sin acentos y en minúsculas) ---
# No marcar "no quiero morir": se descarta si lo precede una negación.
_NEG = r"(?<!no )(?<!nunca )(?<!jamas )"
# A quién se puede querer "irse con": pronombres y la pareja o los padres (los más probables
# en un duelo). A propósito NO incluye hijos ni nietos: "quiero irme con mi hija" suele
# significar mudarse con ella y no es una señal de riesgo.
_CON_FALLECIDO = r"(?:el|ella|mi (?:esposo|esposa|marido|mujer|mama|papa|madre|padre)|mis padres)"
# Preferencias sobre el final de la vida ("quiero morir en mi casa", "en paz"):
# no son rojo; las recoge una categoría amarilla aparte.
_FINAL_DE_VIDA = (
    r"(?:\s+en\s+(?:mi|su|paz|casa|cama)\b|\s+tranquil[oa]|\s+dormid[oa]|"
    r"\s+de viejo|\s+cuando\s+(?:me toque|sea|dios))"
)

_ROJO = {
    "deseo_de_morir": [
        _NEG + r"\bquiero morir(?:me)?(?!" + _FINAL_DE_VIDA + r")",
        _NEG + r"\bquisiera morir(?:me)?(?!" + _FINAL_DE_VIDA + r")",
        r"\bojala (?:me )?muriera", r"\bojala me muera", r"\bojala no despertar",
        r"\bno quiero (?:seguir )?(?:vivir|viviendo)", r"\bprefiero estar muert[oa]",
        r"\bmejor estar muert[oa]",
    ],
    "sin_razon_para_vivir": [
        r"\bpara que vivir", r"\bpara que sigo viviendo", r"\bno vale la pena vivir",
        r"\bno tengo (?:ningun )?motivo para vivir", r"\bno tengo razon(?:es)? para vivir",
    ],
    "autolesion_o_suicidio": [
        r"\bquitarme la vida", r"\bmatarme", r"\bme (?:voy a|quiero|quisiera|podria) matar",
        r"\bsuicidarme", r"\bme voy a suicidar", r"\bacabar con mi vida",
        r"\bterminar con mi vida", r"\bacabar con todo", r"\bhacerme dano", r"\blastimarme",
        r"\bcortarme (?:las )?(?:venas|munecas)", r"\btomarme (?:todas )?las pastillas",
        r"\bahorcarme", r"\bno quiero despertar", r"\bdejar de existir",
    ],
    "plan_de_hacerse_dano": [r"\bya se como (?:hacerlo|quitarme)"],
    "reunirse_con_fallecido": [
        r"\bquiero irme con " + _CON_FALLECIDO + r"\b", r"\bquisiera irme con " + _CON_FALLECIDO + r"\b",
        r"\bme quiero ir con " + _CON_FALLECIDO + r"\b", r"\bquiero reunirme con " + _CON_FALLECIDO + r"\b",
    ],
    "despedida_o_carga": [
        r"\bme quiero despedir", r"\besta es mi despedida", r"\bestarian mejor sin mi",
        r"\bestaria mejor sin mi", r"\bnadie me va a extranar",
    ],
}

_AMARILLO = {
    "desesperanza": [
        r"\bno tiene sentido", r"\bya nada (?:tiene sentido|importa)", r"\bno le encuentro sentido",
        r"\bno veo (?:salida|esperanza|futuro)", r"\bpara que seguir", r"\bsin esperanza",
        r"\bno vale la pena\b", r"\bno tiene caso", r"\bya no puedo mas", r"\bno aguanto mas",
        r"\bno puedo con esto", r"\bnada me (?:importa|ilusiona)",
    ],
    "deseo_pasivo_de_morir": [
        r"\bque dios me (?:lleve|recoja)", r"\bya quiero que (?:me )?(?:lleve|recoja) (?:dios|el senor)",
        r"\bya vivi lo suficiente", r"\bquiero irme de este mundo", r"\bquisiera irme de este mundo",
        r"\bquisiera desaparecer", r"\bquiero desaparecer", r"\bno quiero (?:seguir|estar) aqui",
    ],
    "deseo_de_morir_ambiguo": [
        # "quiero morir en mi casa / en paz": preferencia sobre el final de la vida o deseo
        # de morir; no se puede distinguir, así que se avisa sin activar el mensaje de crisis.
        _NEG + r"\bquiero morir(?:me)?" + _FINAL_DE_VIDA,
        _NEG + r"\bquisiera morir(?:me)?" + _FINAL_DE_VIDA,
    ],
    "deseo_de_estar_con_fallecido": [
        r"\bquiero estar con (?:el|ella)\b", r"\bestar con (?:el|ella) (?:en el cielo|alla)",
    ],
    "sentirse_carga": [r"\bsoy una carga", r"\bsoy un estorbo", r"\bles estorbo"],
    "aislamiento": [
        r"\bmuy sol[oa]\b", r"\bnadie me (?:escucha|quiere|visita|entiende|busca|llama)",
        r"\bno tengo a nadie", r"\bno quiero ver a nadie",
    ],
    "descuido_personal": [
        r"\bno (?:como|duermo|me levanto|salgo)\b", r"\bno puedo dormir", r"\bya no (?:como|duermo)\b",
        r"\bno tengo ganas de (?:nada|comer|levantarme)", r"\bdeje de tomar mis medicinas",
        r"\bno tomo mis medicinas",
    ],
    "culpa_intensa": [r"\bes mi culpa\b", r"\bfue mi culpa\b", r"\bno me lo perdono", r"\bno merezco"],
    # Puede referirse a un tercero (duelo por suicidio): se avisa, pero no es rojo.
    "mencion_de_suicidio": [r"\bsuicid"],
}

_ROJO_RE = {c: [re.compile(p) for p in ps] for c, ps in _ROJO.items()}
_AMARILLO_RE = {c: [re.compile(p) for p in ps] for c, ps in _AMARILLO.items()}

# Texto fijo del nivel ROJO. Lo dice la aplicación tal cual; el modelo de lenguaje no lo genera.
RESPUESTA_ROJO = (
    "Gracias por decírmelo, sé que no es fácil. Lo que siente es muy doloroso y me importa "
    "mucho que usted esté a salvo. No tiene que enfrentarlo en soledad. Por favor, en este "
    "momento busque a una persona de confianza que esté cerca y quédese acompañado. También "
    "voy a avisarle a su tanatólogo."
)

# Instrucción adicional para el modelo cuando hay señales AMARILLAS.
NOTA_AMARILLO = (
    "ATENCIÓN: la persona muestra señales de malestar importante. Responda con especial "
    "cuidado y calidez, reconozca lo que siente sin minimizarlo ni darle la razón en que no "
    "vale la pena seguir, y con suavidad anímela a hablar también con su tanatólogo o con "
    "alguien de confianza. No dé consejos médicos ni haga preguntas que la lleven más hondo "
    "en el dolor."
)

# Cómo se nombra cada categoría ante el tanatólogo (en tercera persona, sin citar frases).
ETIQUETAS = {
    "deseo_de_morir": "expresó deseo de morir",
    "sin_razon_para_vivir": "dijo no encontrar razones para vivir",
    "autolesion_o_suicidio": "habló de hacerse daño o quitarse la vida",
    "plan_de_hacerse_dano": "mencionó saber cómo hacerse daño",
    "reunirse_con_fallecido": "expresó querer reunirse con una persona fallecida",
    "despedida_o_carga": "se despidió o dijo que los demás estarían mejor sin su presencia",
    "desesperanza": "mostró desesperanza",
    "deseo_pasivo_de_morir": "expresó un deseo pasivo de morir",
    "deseo_de_morir_ambiguo": "habló de querer morir en ciertas circunstancias (puede ser una preferencia sobre el final de la vida)",
    "deseo_de_estar_con_fallecido": "dijo querer estar con una persona fallecida",
    "sentirse_carga": "dijo sentirse una carga para otros",
    "aislamiento": "expresó soledad o aislamiento",
    "descuido_personal": "mencionó descuido personal (sueño, alimentación o medicinas)",
    "culpa_intensa": "expresó culpa intensa",
    "mencion_de_suicidio": "mencionó el suicidio (puede referirse a otra persona)",
}

def etiqueta(categoria: str) -> str:
    """Nombre legible de una categoría (si no está en la lista, se arma con su id)."""
    return ETIQUETAS.get(categoria, categoria.replace("_", " "))

@dataclass
class ResultadoRiesgo:
    nivel: str = "verde"
    categorias: list[str] = field(default_factory=list)


def _normalizar(texto: str) -> str:
    """Minúsculas y sin acentos (la ñ queda como n)."""
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    sin_marcas = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", sin_marcas)


def clasificar(texto: str) -> ResultadoRiesgo:
    """Devuelve el nivel y las categorías que lo causaron (no la frase)."""
    limpio = _normalizar(texto)
    rojas = [c for c, ps in _ROJO_RE.items() if any(p.search(limpio) for p in ps)]
    if rojas:
        return ResultadoRiesgo("rojo", sorted(rojas))
    amarillas = [c for c, ps in _AMARILLO_RE.items() if any(p.search(limpio) for p in ps)]
    if amarillas:
        return ResultadoRiesgo("amarillo", sorted(amarillas))
    return ResultadoRiesgo()


def respuesta_rojo() -> str:
    """Texto fijo de nivel rojo, más los recursos de ayuda si se configuraron."""
    if settings.texto_recursos_ayuda.strip():
        return f"{RESPUESTA_ROJO} {settings.texto_recursos_ayuda.strip()}"
    return RESPUESTA_ROJO