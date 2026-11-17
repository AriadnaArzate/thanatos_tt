"""Alta, listado, búsqueda y PIN de pacientes. Solo lo hace el tanatólogo."""
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Rol, Usuario
from app.schemas import NuevoPacienteIn, NuevoPinOut, PacienteCreadoOut, UsuarioOut
from app.security import hashear_password, requiere_rol

router = APIRouter(prefix="/pacientes", tags=["pacientes"])

SoloTanatologo = Annotated[Usuario, Depends(requiere_rol(Rol.TANATOLOGO))]


def _numero_paciente_nuevo(db: Session) -> str:
    """ID de 6 dígitos (el XXXXXX del mockup). Sin repetirse."""
    for _ in range(50):
        numero = str(100000 + secrets.randbelow(900000))
        if db.scalar(select(Usuario.id).where(
            (Usuario.numero_paciente == numero) | (Usuario.usuario == numero)
        )) is None:
            return numero
    raise HTTPException(500, "No se pudo generar el número de paciente. Intente de nuevo.")


def _pin_nuevo() -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(6))


@router.post("", response_model=PacienteCreadoOut, status_code=201)
def crear_paciente(datos: NuevoPacienteIn, tanatologo: SoloTanatologo,
                   db: Annotated[Session, Depends(get_db)]):
    """Registra al paciente. El sistema genera su ID y su PIN de 6 dígitos y se los
    devuelve al tanatólogo, que se los entrega al adulto mayor: con ellos inicia
    sesión (ID como usuario, PIN como contraseña). El tanatólogo busca al paciente
    por su ID. El PIN solo se muestra aquí; después no se puede consultar."""
    numero = _numero_paciente_nuevo(db)
    pin = _pin_nuevo()
    paciente = Usuario(
        nombre=datos.nombre.strip(),
        usuario=numero,                          # el ID es el usuario de acceso
        password_hash=hashear_password(pin),
        rol=Rol.ADULTO_MAYOR.value,
        tanatologo_id=tanatologo.id,             # queda asignado a quien lo da de alta
        telefono=datos.telefono.strip() if datos.telefono else None,
        edad=datos.edad,
        notif_app=datos.notif_app,
        guia_auditiva=datos.guia_auditiva,
        numero_paciente=numero,
    )
    db.add(paciente)
    db.commit()
    db.refresh(paciente)
    salida = PacienteCreadoOut.model_validate(paciente, from_attributes=True)
    salida.pin = pin
    return salida


@router.get("", response_model=list[UsuarioOut])
def listar_pacientes(
    tanatologo: SoloTanatologo,
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str | None, Query(max_length=60, description="Busca por ID de paciente o por nombre")] = None,
):
    """Solo los pacientes de este tanatólogo. Con `q`, filtra por ID o nombre."""
    consulta = select(Usuario).where(
        Usuario.tanatologo_id == tanatologo.id,
        Usuario.rol == Rol.ADULTO_MAYOR.value,
    )
    if q and q.strip():
        patron = "%" + q.strip().replace("%", "").replace("_", "") + "%"
        consulta = consulta.where(
            Usuario.numero_paciente.like(patron) | Usuario.nombre.ilike(patron)
        )
    return db.scalars(consulta.order_by(Usuario.nombre)).all()


@router.post("/{paciente_id}/nuevo-pin", response_model=NuevoPinOut)
def nuevo_pin(paciente_id: int, tanatologo: SoloTanatologo, db: Annotated[Session, Depends(get_db)]):
    """Genera un PIN nuevo (el anterior deja de funcionar). Sirve cuando el paciente lo
    olvida y para pacientes creados antes de que existieran el ID y el PIN."""
    paciente = db.get(Usuario, paciente_id)
    # Mismo 404 si no existe o si es de otro tanatólogo: no se revela cuál fue.
    if paciente is None or paciente.tanatologo_id != tanatologo.id or paciente.rol != Rol.ADULTO_MAYOR.value:
        raise HTTPException(404, "Paciente no encontrado")
    if not paciente.numero_paciente:
        # Paciente anterior al ID: se le asigna uno y pasa a ser también su usuario de acceso.
        numero = _numero_paciente_nuevo(db)
        paciente.numero_paciente = numero
        paciente.usuario = numero
    pin = _pin_nuevo()
    paciente.password_hash = hashear_password(pin)
    db.commit()
    return NuevoPinOut(numero_paciente=paciente.numero_paciente, pin=pin)