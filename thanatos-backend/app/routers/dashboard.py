"""Dashboard del tanatólogo: semáforo con su razonamiento, resumen de lo hablado,
métricas y alertas de SUS pacientes.

El tanatólogo NO lee las conversaciones ni las cartas. Ve:
  * el semáforo y por qué tiene ese color (categorías detectadas, nunca frases),
  * un resumen por temas de lo que el paciente ha hablado (sin citas textuales),
  * métricas de uso y emociones, y las alertas.
"""
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.db import get_db
from app.security import requiere_rol
from app.services import explicacion, resumenes

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

SoloTanatologo = Annotated[models.Usuario, Depends(requiere_rol(models.Rol.TANATOLOGO))]
BD = Annotated[Session, Depends(get_db)]


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _desde(dias: int) -> datetime:
    return _ahora() - timedelta(days=dias)


def _paciente_de(db: Session, tanatologo: models.Usuario, paciente_id: int) -> models.Usuario:
    """El paciente, solo si es de este tanatólogo (si no, 404)."""
    paciente = db.get(models.Usuario, paciente_id)
    if (paciente is None or paciente.tanatologo_id != tanatologo.id
            or paciente.rol != models.Rol.ADULTO_MAYOR.value):
        raise HTTPException(404, "Paciente no encontrado")
    return paciente


def _senales(db: Session, paciente_id: int, desde: datetime, hasta: datetime | None = None):
    """Señales amarillas o rojas del paciente en [desde, hasta)."""
    consulta = select(models.SenalRiesgo).where(
        models.SenalRiesgo.usuario_id == paciente_id, models.SenalRiesgo.creado_en >= desde
    )
    if hasta is not None:
        consulta = consulta.where(models.SenalRiesgo.creado_en < hasta)
    return db.scalars(consulta.order_by(models.SenalRiesgo.id)).all()


def _alertas_abiertas(db: Session, paciente_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(models.Alerta)
        .where(models.Alerta.usuario_id == paciente_id, models.Alerta.estado != "atendida")
    ) or 0


def _ultimo_mensaje(db: Session, paciente_id: int) -> datetime | None:
    return db.scalar(
        select(func.max(models.Mensaje.creado_en))
        .select_from(models.Mensaje)
        .join(models.Sesion, models.Mensaje.sesion_id == models.Sesion.id)
        .where(models.Sesion.usuario_id == paciente_id, models.Mensaje.rol == "user")
    )


@router.get("/pacientes")
def listar_pacientes(tanatologo: SoloTanatologo, db: BD, dias: int | None = None):
    """Tarjetas del dashboard: un paciente por fila, con su semáforo y el motivo en una línea."""
    dias = dias or settings.dias_semaforo
    pacientes = db.scalars(
        select(models.Usuario).where(
            models.Usuario.tanatologo_id == tanatologo.id,
            models.Usuario.rol == models.Rol.ADULTO_MAYOR.value,
        ).order_by(models.Usuario.nombre)
    ).all()

    filas = []
    for p in pacientes:
        senales = _senales(db, p.id, _desde(dias))
        ultima_emocion = db.scalar(
            select(models.RegistroEmocion.emocion)
            .where(models.RegistroEmocion.usuario_id == p.id)
            .order_by(models.RegistroEmocion.id.desc())
            .limit(1)
        )
        filas.append({
            "id": p.id, "nombre": p.nombre, "usuario": p.usuario,
            "semaforo": explicacion.nivel_maximo(senales),
            "motivo": explicacion.motivo_corto(senales),
            "ultima_actividad": _ultimo_mensaje(db, p.id),
            "ultima_emocion": ultima_emocion,
            "alertas_abiertas": _alertas_abiertas(db, p.id),
        })
    return filas


@router.get("/pacientes/{paciente_id}/explicacion")
def explicacion_paciente(paciente_id: int, tanatologo: SoloTanatologo, db: BD,
                         dias: int | None = None):
    """Por qué el paciente tiene ese color, más el último resumen generado (si hay)."""
    dias = dias or settings.dias_semaforo
    paciente = _paciente_de(db, tanatologo, paciente_id)
    senales = _senales(db, paciente.id, _desde(dias))
    previas = len(_senales(db, paciente.id, _desde(dias * 2), _desde(dias)))
    info = explicacion.explicar(senales, previas, dias, _alertas_abiertas(db, paciente.id))

    ultimo = db.scalar(
        select(models.ResumenPaciente)
        .where(models.ResumenPaciente.usuario_id == paciente.id)
        .order_by(models.ResumenPaciente.id.desc())
        .limit(1)
    )
    resumen = None
    if ultimo is not None:
        reciente = _ultimo_mensaje(db, paciente.id)
        resumen = {
            "texto": ultimo.texto, "generado_en": ultimo.generado_en,
            "mensajes_considerados": ultimo.num_mensajes,
            # True si el paciente habló después de generarse: conviene actualizarlo.
            "desactualizado": reciente is not None and reciente > ultimo.generado_en,
        }
    return {"paciente": {"id": paciente.id, "nombre": paciente.nombre},
            "periodo_dias": dias, **info, "resumen": resumen}


@router.post("/pacientes/{paciente_id}/resumen-conversaciones")
async def generar_resumen(paciente_id: int, tanatologo: SoloTanatologo, db: BD, dias: int = 7):
    """Genera (y guarda) un resumen por temas de lo que el paciente habló en los últimos
    `dias`. Tarda como una respuesta del modelo (decenas de segundos): la app debe mostrar
    "generando...". Las cartas y los relatos que la persona guarda NO se incluyen."""
    paciente = _paciente_de(db, tanatologo, paciente_id)
    desde = _desde(dias)
    frases = db.scalars(
        select(models.Mensaje.texto)
        .select_from(models.Mensaje)
        .join(models.Sesion, models.Mensaje.sesion_id == models.Sesion.id)
        .where(models.Sesion.usuario_id == paciente.id, models.Mensaje.rol == "user",
               models.Mensaje.creado_en >= desde)
        .order_by(models.Mensaje.id)
    ).all()
    if not frases:
        raise HTTPException(404, "Este paciente no ha conversado en ese periodo.")

    try:
        texto = await resumenes.resumir(list(frases))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, "El motor conversacional no está disponible.") from exc

    registro = models.ResumenPaciente(
        usuario_id=paciente.id, desde=desde, hasta=_ahora(), num_mensajes=len(frases), texto=texto
    )
    db.add(registro)
    db.commit()
    return {"texto": registro.texto, "generado_en": registro.generado_en,
            "mensajes_considerados": registro.num_mensajes, "desactualizado": False}


@router.get("/pacientes/{paciente_id}/resumen")
def metricas_paciente(paciente_id: int, tanatologo: SoloTanatologo, db: BD, dias: int = 7):
    """Métricas de uso y emociones de un paciente en los últimos `dias`."""
    paciente = _paciente_de(db, tanatologo, paciente_id)
    desde = _desde(dias)

    emociones = db.scalars(
        select(models.RegistroEmocion)
        .where(models.RegistroEmocion.usuario_id == paciente.id,
               models.RegistroEmocion.creado_en >= desde)
        .order_by(models.RegistroEmocion.id)
    ).all()
    tipos_sesion = db.scalars(
        select(models.Sesion.tipo)
        .where(models.Sesion.usuario_id == paciente.id, models.Sesion.iniciada_en >= desde)
    ).all()
    niveles_alerta = db.scalars(
        select(models.Alerta.nivel)
        .where(models.Alerta.usuario_id == paciente.id, models.Alerta.creado_en >= desde)
    ).all()

    ejercicios_mostrados = db.scalars(
        select(models.EjercicioMostrado.ejercicio)
        .where(models.EjercicioMostrado.usuario_id == paciente.id,
               models.EjercicioMostrado.creado_en >= desde)
    ).all()

    return {
        "paciente": {"id": paciente.id, "nombre": paciente.nombre},
        "dias": dias,
        "semaforo": explicacion.nivel_maximo(_senales(db, paciente.id, desde)),
        "emociones_conteo": dict(Counter(e.emocion for e in emociones)),
        "emociones_linea_de_tiempo": [
            {"emocion": e.emocion, "intensidad": e.intensidad, "creado_en": e.creado_en}
            for e in emociones[-30:]
        ],
        "sesiones_por_tipo": dict(Counter(tipos_sesion)),
        "alertas_por_nivel": dict(Counter(niveles_alerta)),
        "ejercicios_sugeridos": dict(Counter(ejercicios_mostrados)),
    }


@router.get("/alertas")
def listar_alertas(
    tanatologo: SoloTanatologo,
    db: BD,
    estado: Literal["abiertas", "nueva", "vista", "atendida", "todas"] = "abiertas",
):
    consulta = (
        select(models.Alerta, models.Usuario.nombre)
        .join(models.Usuario, models.Alerta.usuario_id == models.Usuario.id)
        .where(models.Alerta.tanatologo_id == tanatologo.id)
        .order_by(models.Alerta.id.desc())
    )
    if estado == "abiertas":
        consulta = consulta.where(models.Alerta.estado != "atendida")
    elif estado != "todas":
        consulta = consulta.where(models.Alerta.estado == estado)

    return [
        {"id": a.id, "paciente_id": a.usuario_id, "paciente": nombre, "origen": a.origen,
         "nivel": a.nivel, "motivo": a.motivo, "estado": a.estado,
         "creado_en": a.creado_en, "atendida_en": a.atendida_en}
        for a, nombre in db.execute(consulta).all()
    ]


class EstadoIn(BaseModel):
    estado: Literal["vista", "atendida"]


@router.patch("/alertas/{alerta_id}")
def cambiar_estado_alerta(alerta_id: int, datos: EstadoIn, tanatologo: SoloTanatologo, db: BD):
    alerta = db.get(models.Alerta, alerta_id)
    if alerta is None or alerta.tanatologo_id != tanatologo.id:
        raise HTTPException(404, "Alerta no encontrada")
    alerta.estado = datos.estado
    alerta.atendida_en = _ahora() if datos.estado == "atendida" else None
    db.commit()
    return {"id": alerta.id, "estado": alerta.estado, "atendida_en": alerta.atendida_en}