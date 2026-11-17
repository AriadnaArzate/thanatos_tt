"""
Ejercicios de desahogo (botón "Ejercicios de desahogo" del menú).

La aplicación NO guía el ejercicio paso a paso: cada vez que la persona abre esa
opción se elige UNO al azar y el motor conversacional se lo EXPLICA en voz, para
que lo haga por su cuenta (en papel, en voz alta, con un familiar...).

Cada ejercicio trae los datos con los que el modelo redacta la explicación
(objetivo, pasos, duración) y un texto de respaldo fijo, que se usa si el modelo
no está disponible o su explicación no cumple (por ejemplo, si tutea).

TODOS los textos son de versión 1 y los debe revisar la tanatóloga [VALIDAR].
(Técnicas que ella mencionó y que pueden sumarse: sacar el enojo, favorecer el
desahogo con el llanto y la carta del perdón.)
"""
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Ejercicio:
    id: str
    nombre: str                 # cómo se nombra ante la persona
    objetivo: str               # qué se busca con el ejercicio
    pasos: tuple[str, ...]      # lo que se debe hacer, en orden (el modelo SOLO usa estos)
    duracion: str               # cuánto puede tomar
    texto_respaldo: str         # explicación fija, sin modelo


# Se agrega SIEMPRE al final de la explicación (lo dice la aplicación, no el modelo): como el
# ejercicio se hace sin acompañamiento, se recuerda cómo pedir ayuda. [VALIDAR]
CIERRE = (
    "Tómese el tiempo que necesite. Si en algún momento se siente muy mal, puede detenerse y "
    "avisar a su tanatólogo desde la opción de contactarlo. Si desea, después puede contarme cómo le fue."
)

_EJERCICIOS = [
    Ejercicio(
        id="reminiscencia",
        nombre="Compartir un recuerdo",
        objetivo="Revivir con cariño un recuerdo importante y reconocer lo que significa para usted.",
        pasos=(
            "Busque un lugar tranquilo y siéntese con comodidad. Si le ayuda, tenga a la mano una fotografía.",
            "Elija un recuerdo que sea importante para usted: un lugar, una fecha o un momento con alguien querido.",
            "Recuérdelo con calma: dónde estaba, quién estaba con usted y qué sentía.",
            "Si lo desea, cuéntelo a una persona de confianza o anótelo en un cuaderno.",
        ),
        duracion="unos 10 a 15 minutos",
        texto_respaldo=(
            "Hoy le propongo compartir un recuerdo. Busque un lugar tranquilo y siéntese con comodidad; "
            "si quiere, tenga a la mano una fotografía. Elija un recuerdo importante para usted y revívalo "
            "con calma: dónde estaba, quién estaba con usted y qué sentía. Si lo desea, cuéntelo a alguien "
            "de confianza o anótelo en un cuaderno. Puede tomarse unos diez a quince minutos."
        ),
    ),
    Ejercicio(
        id="cartas_simbolicas",
        nombre="Escribir una carta",
        objetivo="Decir lo que quedó pendiente a alguien que ya no está, o con quien hay algo sin resolver.",
        pasos=(
            "Piense a quién quiere dirigir la carta: alguien que ya no está, o alguien con quien le quedó algo pendiente.",
            "Con papel y pluma, escriba lo que quiera decirle: lo que agradece, lo que extraña, lo que no alcanzó a decir.",
            "No tiene que entregarla ni enseñarla a nadie; es solo para usted.",
            "Al terminar, puede leerla en voz alta, guardarla en un lugar especial o compartirla con alguien de confianza.",
        ),
        duracion="unos 15 a 20 minutos",
        texto_respaldo=(
            "Hoy le propongo escribir una carta. Piense a quién quiere dirigirla: alguien que ya no está, "
            "o alguien con quien le quedó algo pendiente. Con papel y pluma, escriba lo que quiera decirle: "
            "lo que agradece, lo que extraña y lo que no alcanzó a decir. No tiene que entregarla ni "
            "enseñarla a nadie. Al terminar, puede leerla en voz alta o guardarla en un lugar especial. "
            "Puede tomarse unos quince a veinte minutos."
        ),
    ),
    Ejercicio(
        id="legado_emocional",
        nombre="Dejar mi legado",
        objetivo="Reunir lo que usted aprendió y lo que desea que su familia recuerde.",
        pasos=(
            "Piense en lo que aprendió de la persona que perdió, o en lo que la vida le ha enseñado.",
            "Elija tres cosas: una enseñanza, un recuerdo que no quiere que su familia olvide y un consejo que quiera dejar.",
            "Anótelas en un cuaderno o cuéntelas a un familiar.",
        ),
        duracion="unos 15 minutos",
        texto_respaldo=(
            "Hoy le propongo reunir lo que usted quiere dejar a su familia. Piense en lo que aprendió de la "
            "persona que perdió, o en lo que la vida le ha enseñado. Elija tres cosas: una enseñanza, un "
            "recuerdo que no quiere que su familia olvide y un consejo que quiera dejar. Anótelas en un "
            "cuaderno o cuéntelas a un familiar. Puede tomarse unos quince minutos."
        ),
    ),
    Ejercicio(
        id="expresion_emocional",
        nombre="Contar cómo me siento",
        objetivo="Ponerle nombre a lo que siente y permitirse sentirlo sin juzgarse.",
        pasos=(
            "Elija un momento tranquilo y respire despacio unas cuantas veces.",
            "Pregúntese cómo se siente hoy y póngale un nombre a esa emoción.",
            "Permítase sentirla sin juzgarse: no hay emociones buenas ni malas.",
            "Si lo desea, dígala en voz alta, escríbala en una hoja o platíquela con alguien de confianza.",
        ),
        duracion="unos 10 minutos",
        texto_respaldo=(
            "Hoy le propongo contar cómo se siente. Elija un momento tranquilo y respire despacio unas "
            "cuantas veces. Pregúntese cómo se siente hoy y póngale un nombre a esa emoción. Permítase "
            "sentirla sin juzgarse, porque no hay emociones buenas ni malas. Si lo desea, dígala en voz "
            "alta, escríbala en una hoja o platíquela con alguien de confianza. Puede tomarse unos diez minutos."
        ),
    ),
]

_POR_ID = {e.id: e for e in _EJERCICIOS}


def listar() -> list[Ejercicio]:
    return list(_EJERCICIOS)


def obtener(ejercicio_id: str) -> Ejercicio | None:
    return _POR_ID.get(ejercicio_id)


def sortear(excluir: str | None = None) -> Ejercicio:
    """Un ejercicio al azar. Si se indica `excluir` (el último que se le mostró a la
    persona), no se repite el mismo dos veces seguidas."""
    candidatos = [e for e in _EJERCICIOS if e.id != excluir] or _EJERCICIOS
    return random.choice(candidatos)


def respaldo_completo(ejercicio: Ejercicio) -> str:
    """Texto fijo completo (explicación de respaldo + cierre)."""
    return f"{ejercicio.texto_respaldo} {CIERRE}"