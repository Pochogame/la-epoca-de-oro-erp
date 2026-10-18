from sqlalchemy import func

from app.models.contabilidad import Asiento, AsientoLinea, CuentaContable, GastoOperativo
from app.repositories.base import RepositorioBase


class CuentaContableRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(CuentaContable)

    def por_codigo(self, codigo):
        return CuentaContable.query.filter_by(codigo=codigo).first()

    def catalogo(self):
        return CuentaContable.query.order_by(CuentaContable.codigo).all()


class AsientoRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(Asiento)

    def siguiente_folio(self):
        ultimo = Asiento.query.order_by(Asiento.id.desc()).first()
        numero = (ultimo.id + 1) if ultimo else 1
        return f"AST-{numero:05d}"

    def en_rango(self, desde, hasta):
        return (
            Asiento.query.filter(Asiento.fecha >= desde, Asiento.fecha <= hasta)
            .order_by(Asiento.fecha, Asiento.id)
            .all()
        )

    def recientes(self, limite=200):
        return Asiento.query.order_by(Asiento.fecha.desc(), Asiento.id.desc()).limit(limite).all()

    def saldo_cuenta(self, codigo):
        total = (
            AsientoLinea.query.join(CuentaContable)
            .filter(CuentaContable.codigo == codigo)
            .with_entities(
                func.coalesce(func.sum(AsientoLinea.debe), 0.0),
                func.coalesce(func.sum(AsientoLinea.haber), 0.0),
            )
            .first()
        )
        return round(float(total[0]) - float(total[1]), 2)


class GastoRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(GastoOperativo)

    def recientes(self, limite=200):
        return GastoOperativo.query.order_by(GastoOperativo.fecha.desc()).limit(limite).all()

    def en_rango(self, desde, hasta):
        return (
            GastoOperativo.query.filter(GastoOperativo.fecha >= desde, GastoOperativo.fecha <= hasta)
            .order_by(GastoOperativo.fecha)
            .all()
        )

    def pendientes(self):
        return (
            GastoOperativo.query.filter_by(estado="PENDIENTE")
            .order_by(GastoOperativo.fecha)
            .all()
        )
