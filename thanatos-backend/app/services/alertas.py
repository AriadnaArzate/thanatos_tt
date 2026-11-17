"""Alertas para el tanatólogo (riesgo detectado o solicitud de contacto)."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alerta, Usuario
from app.services import notificaciones

logger = logging.getLogger("thanatos.alertas")


def crear_alerta(
    db: Session,
    paciente: Usuario,
    *,
    origen: str,            # "riesgo" o "contacto"
    nivel: str,             # "amarillo", "rojo" o "contacto"
    motivo: str,            # categorías detectadas, NO la frase completa (privacidad)
    sesion_id: str | None = None,
) -> Alerta:
    # Si ya hay una alerta SIN LEER igual para esta sesión, no se duplica:
    # así el tanatólogo no recibe diez avisos por la misma conversación.
    misma_sesion = Alerta.sesion_id == sesion_id if sesion_id else Alerta.sesion_id.is_(None)
    existente = db.scalar(
        select(Alerta).where(
            Alerta.usuario_id == paciente.id, Alerta.origen == origen,
            Alerta.nivel == nivel, Alerta.estado == "nueva", misma_sesion,
        )
    )
    if existente is not None:
        return existente

    alerta = Alerta(
        usuario_id=paciente.id, tanatologo_id=paciente.tanatologo_id, sesion_id=sesion_id,
        origen=origen, nivel=nivel, motivo=motivo[:200],
    )
    db.add(alerta)
    db.commit()
    _avisar(db, paciente, alerta)
    return alerta


def _avisar(db: Session, paciente: Usuario, alerta: Alerta) -> None:
    if paciente.tanatologo_id is None:
        logger.warning("Alerta %s sin tanatólogo asignado: nadie fue avisado.", alerta.id)
        return
    tanatologo = db.get(Usuario, paciente.tanatologo_id)
    texto = (f"Thanatos: alerta {alerta.nivel.upper()} de {paciente.nombre} "
             f"({alerta.motivo}). Revise el dashboard.")
    try:
        notificaciones.enviar_whatsapp(tanatologo.telefono if tanatologo else None, texto)
    except Exception:  # noqa: BLE001 - un fallo de aviso no debe romper la conversación
        logger.exception("No se pudo enviar el aviso de la alerta %s", alerta.id)