"""Formas de los datos que entran y salen de la API (validación con Pydantic)."""
from pydantic import BaseModel, ConfigDict, Field

# Validación sencilla de correo (sin dependencias extra).
_CORREO = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
# Teléfono: dígitos, +, espacios o guiones.
_TELEFONO = r"^[0-9+\- ]{8,30}$"


class NuevoUsuarioIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    usuario: str = Field(min_length=3, max_length=60, pattern=r"^[A-Za-z0-9_.-]+$")
    # bcrypt solo considera los primeros 72 bytes, por eso el tope.
    password: str = Field(min_length=8, max_length=72)


class RegistroTanatologoIn(BaseModel):
    """Registro de un tanatólogo desde la pantalla de inicio de sesión.
    El correo es también su nombre de usuario para entrar."""
    nombre: str = Field(min_length=2, max_length=120)
    correo: str = Field(max_length=60, pattern=_CORREO)
    password: str = Field(min_length=8, max_length=72)
    telefono: str | None = Field(default=None, pattern=_TELEFONO)
    # Solo se exige si el servidor tiene CODIGO_REGISTRO_TANATOLOGO configurado.
    codigo: str | None = Field(default=None, max_length=100)


class PerfilIn(BaseModel):
    """Pantalla "Información del Tanatólogo" (Guardar/Editar). Todo es opcional:
    solo se cambia lo que se envía."""
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    correo: str | None = Field(default=None, max_length=60, pattern=_CORREO)
    telefono: str | None = Field(default=None, pattern=_TELEFONO)


class NuevoPacienteIn(BaseModel):
    """Pantalla "Registro de Paciente". El ID y el PIN los genera el sistema."""
    nombre: str = Field(min_length=2, max_length=120)
    edad: int | None = Field(default=None, ge=1, le=120)
    # Teléfono del paciente (el del tanatólogo vive en su propio perfil).
    telefono: str | None = Field(default=None, pattern=_TELEFONO)
    notif_app: bool = True
    guia_auditiva: bool = False


class UsuarioOut(BaseModel):
    """Lo que devolvemos de un usuario. Nunca incluye el hash de la contraseña."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    usuario: str
    rol: str
    correo: str | None = None
    telefono: str | None = None
    edad: int | None = None
    notif_app: bool | None = None
    guia_auditiva: bool | None = None
    numero_paciente: str | None = None


class PacienteCreadoOut(UsuarioOut):
    # El PIN solo se muestra aquí, una vez. Después no se puede recuperar
    # (solo se guarda su hash): si se pierde, se genera uno nuevo.
    pin: str


class NuevoPinOut(BaseModel):
    numero_paciente: str | None
    pin: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"