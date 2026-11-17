"""
Migraciones mínimas para SQLite. `create_all` crea tablas NUEVAS pero no agrega
columnas a tablas que ya existen; esto cubre ese hueco para que no haga falta
borrar la base ni los usuarios. Se ejecuta al arrancar y es seguro repetirlo.
"""
import logging

from sqlalchemy import inspect, text

from app import models  # noqa: F401  (registra las tablas en Base)
from app.db import Base, engine

logger = logging.getLogger("thanatos.migraciones")

# (tabla, columna, definición SQL) de columnas agregadas después de la primera versión.
_COLUMNAS_NUEVAS = [
    ("sesiones", "tipo", "VARCHAR(30) NOT NULL DEFAULT 'conversacion'"),
    ("usuarios", "telefono", "VARCHAR(30)"),
]


def aplicar() -> None:
    Base.metadata.create_all(engine)   # crea las tablas nuevas que falten
    for tabla, columna, definicion in _COLUMNAS_NUEVAS:
        existentes = {c["name"] for c in inspect(engine).get_columns(tabla)}
        if columna not in existentes:
            with engine.begin() as conexion:
                conexion.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}"))
            logger.info("Migración: se agregó la columna %s.%s", tabla, columna)