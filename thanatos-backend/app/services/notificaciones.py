"""
Avisos al tanatólogo. La integración REAL con la API de WhatsApp está pendiente:
mientras WHATSAPP_ACTIVO sea false, los avisos solo se registran en el log.
"""
import logging

from app.config import settings

logger = logging.getLogger("thanatos.notificaciones")


def _enmascarar(telefono: str) -> str:
    return "***" + telefono[-4:] if len(telefono) > 4 else "***"


def enviar_whatsapp(telefono: str | None, texto: str) -> bool:
    """True si el aviso se envió (o se simuló). Nunca lanza errores hacia afuera."""
    if not telefono:
        logger.warning("Aviso sin enviar: el tanatólogo no tiene teléfono registrado.")
        return False
    if not settings.whatsapp_activo:
        logger.info("[SIMULADO] WhatsApp a %s: %s", _enmascarar(telefono), texto)
        return True
    logger.error("WHATSAPP_ACTIVO=true pero la integración con la API aún no está implementada.")
    return False