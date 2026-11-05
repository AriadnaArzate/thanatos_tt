"""Formas de los datos que entran y salen de la API (validación con Pydantic)."""
from pydantic import BaseModel, ConfigDict, Field


class NuevoUsuarioIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    usuario: str = Field(min_length=3, max_length=60, pattern=r"^[A-Za-z0-9_.-]+$")
    # bcrypt solo considera los primeros 72 bytes, por eso el tope.
    password: str = Field(min_length=8, max_length=72)


class UsuarioOut(BaseModel):
    """Lo que devolvemos de un usuario. Nunca incluye el hash de la contraseña."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    usuario: str
    rol: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"