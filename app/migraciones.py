"""Micro-migraciones para SQLite: agrega columnas nuevas a bases existentes
sin necesidad de borrar los datos. Es idempotente: si la columna ya existe,
el error se ignora.
"""

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.extensions import db

COLUMNAS_NUEVAS = (
    ("ventas", "mesa_id", "INTEGER REFERENCES mesas(id)"),
    ("ventas", "cancelada", "BOOLEAN NOT NULL DEFAULT 0"),
    ("ventas", "cancelada_en", "DATETIME"),
    ("ventas", "motivo_cancelacion", "VARCHAR(200) DEFAULT ''"),
    ("comandas", "merma_en", "DATETIME"),
    ("comandas", "motivo_merma", "VARCHAR(200) DEFAULT ''"),
    ("comandas", "cerrada_en", "DATETIME"),
    ("comandas", "cerrada_por_id", "INTEGER REFERENCES usuarios(id)"),
)


def aplicar_migraciones():
    for tabla, columna, definicion in COLUMNAS_NUEVAS:
        if not _tabla_existe(tabla):
            continue
        if _columna_existe(tabla, columna):
            continue
        try:
            db.session.execute(
                text(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")
            )
            db.session.commit()
        except OperationalError:
            db.session.rollback()


def _tabla_existe(tabla):
    resultado = db.session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:tabla"),
        {"tabla": tabla},
    ).first()
    return resultado is not None


def _columna_existe(tabla, columna):
    filas = db.session.execute(text(f"PRAGMA table_info({tabla})")).fetchall()
    return any(fila[1] == columna for fila in filas)
