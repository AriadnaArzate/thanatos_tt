"""Crea una cuenta de tanatólogo. Los tanatólogos NO se registran por la API
(si no, cualquiera podría hacerse pasar por uno y ver datos de pacientes).

Uso, desde thanatos-backend con .venv activo:  python scripts/crear_tanatologo.py
"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app import models  # noqa: E402,F401  (registra las tablas)
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import Rol, Usuario  # noqa: E402
from app.security import hashear_password  # noqa: E402


def main() -> None:
    Base.metadata.create_all(engine)
    nombre = input("Nombre completo: ").strip()
    usuario = input("Usuario: ").strip().lower()
    password = getpass.getpass("Contraseña (mínimo 8 caracteres): ")
    if len(nombre) < 2 or len(usuario) < 3 or not 8 <= len(password) <= 72:
        sys.exit("Datos inválidos: revisa longitudes (contraseña de 8 a 72 caracteres).")

    with SessionLocal() as db:
        if db.scalar(select(Usuario).where(Usuario.usuario == usuario)):
            sys.exit("Ese usuario ya existe.")
        db.add(Usuario(nombre=nombre, usuario=usuario,
                       password_hash=hashear_password(password), rol=Rol.TANATOLOGO.value))
        db.commit()
    print(f"Tanatólogo '{usuario}' creado.")


if __name__ == "__main__":
    main()