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
    ("ventas", "cuenta_id", "INTEGER REFERENCES cuentas_mesa(id)"),
    ("ventas", "cobrada_en", "DATETIME"),
    ("ventas", "cliente_id", "INTEGER REFERENCES clientes(id)"),
    ("cuentas_mesa", "cliente_id", "INTEGER REFERENCES clientes(id)"),
    ("comandas", "merma_en", "DATETIME"),
    ("comandas", "motivo_merma", "VARCHAR(200) DEFAULT ''"),
    ("comandas", "cerrada_en", "DATETIME"),
    ("comandas", "cerrada_por_id", "INTEGER REFERENCES usuarios(id)"),
    ("comandas", "ronda", "INTEGER NOT NULL DEFAULT 1"),
    ("venta_detalles", "variante_id", "INTEGER REFERENCES producto_variantes(id)"),
    ("venta_detalles", "variante_nombre", "VARCHAR(40) DEFAULT ''"),
    ("venta_detalles", "cancelado", "BOOLEAN NOT NULL DEFAULT 0"),
    ("venta_detalles", "cancelado_en", "DATETIME"),
    ("venta_detalles", "motivo_cancelacion", "VARCHAR(200) DEFAULT ''"),
    ("venta_detalles", "cancelado_por_id", "INTEGER REFERENCES usuarios(id)"),
    ("venta_detalles", "autorizado_por_id", "INTEGER REFERENCES usuarios(id)"),
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

    _marcar_ventas_historicas_cobradas()
    _consolidar_almacen_principal()


def _consolidar_almacen_principal():
    """Deja un solo almacén operativo (ALM-MP): suma todo el stock ahí,
    apunta los productos a ese almacén y oculta los demás."""
    if not _tabla_existe("almacenes") or not _tabla_existe("stock_almacen"):
        return
    principal = db.session.execute(
        text("SELECT id FROM almacenes WHERE codigo = 'ALM-MP'")
    ).first()
    if principal is None:
        return
    principal_id = principal[0]
    try:
        insumos = db.session.execute(text("SELECT id FROM insumos")).fetchall()
        for (insumo_id,) in insumos:
            total = db.session.execute(
                text(
                    "SELECT COALESCE(SUM(cantidad), 0) FROM stock_almacen "
                    "WHERE insumo_id = :insumo_id"
                ),
                {"insumo_id": insumo_id},
            ).scalar()
            fila = db.session.execute(
                text(
                    "SELECT id FROM stock_almacen "
                    "WHERE insumo_id = :insumo_id AND almacen_id = :almacen_id"
                ),
                {"insumo_id": insumo_id, "almacen_id": principal_id},
            ).first()
            if fila is not None:
                db.session.execute(
                    text("UPDATE stock_almacen SET cantidad = :total WHERE id = :id"),
                    {"total": total or 0.0, "id": fila[0]},
                )
            else:
                db.session.execute(
                    text(
                        "INSERT INTO stock_almacen (insumo_id, almacen_id, cantidad) "
                        "VALUES (:insumo_id, :almacen_id, :total)"
                    ),
                    {
                        "insumo_id": insumo_id,
                        "almacen_id": principal_id,
                        "total": total or 0.0,
                    },
                )
        db.session.execute(
            text("UPDATE stock_almacen SET cantidad = 0 WHERE almacen_id != :id"),
            {"id": principal_id},
        )
        if _tabla_existe("productos"):
            db.session.execute(
                text(
                    "UPDATE productos SET almacen_consumo_id = :almacen_id "
                    "WHERE almacen_consumo_id IS NULL OR almacen_consumo_id != :almacen_id"
                ),
                {"almacen_id": principal_id},
            )
        db.session.commit()
    except OperationalError:
        db.session.rollback()


def _marcar_ventas_historicas_cobradas():
    """Las ventas anteriores a las cuentas de mesa ya estaban pagadas:
    se marcan como cobradas para que reportes y contabilidad las sigan viendo."""
    if not _tabla_existe("ventas") or not _columna_existe("ventas", "cobrada_en"):
        return
    if not _columna_existe("ventas", "cuenta_id"):
        return
    try:
        db.session.execute(
            text(
                "UPDATE ventas SET cobrada_en = fecha "
                "WHERE cobrada_en IS NULL AND cuenta_id IS NULL"
            )
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
