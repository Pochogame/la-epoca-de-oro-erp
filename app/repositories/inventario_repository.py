from app.models.inventario import (
    Almacen,
    AvisoFaltante,
    Insumo,
    Merma,
    MovimientoInventario,
    StockAlmacen,
)
from app.repositories.base import RepositorioBase


class AlmacenRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(Almacen)

    def por_codigo(self, codigo):
        return Almacen.query.filter_by(codigo=codigo).first()

    def principal(self):
        almacen = self.por_codigo("ALM-MP")
        if almacen is not None:
            return almacen
        return Almacen.query.order_by(Almacen.id).first()

    def todos_ordenados(self):
        return Almacen.query.order_by(Almacen.codigo).all()


class InsumoRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(Insumo)

    def por_codigo(self, codigo):
        return Insumo.query.filter_by(codigo=codigo).first()

    def activos(self):
        return Insumo.query.filter_by(activo=True).order_by(Insumo.nombre).all()

    def stock(self, insumo_id, almacen_id):
        return StockAlmacen.query.filter_by(insumo_id=insumo_id, almacen_id=almacen_id).first()

    def asegurar_stock(self, insumo_id, almacen_id):
        stock = self.stock(insumo_id, almacen_id)
        if stock is None:
            stock = StockAlmacen(insumo_id=insumo_id, almacen_id=almacen_id, cantidad=0.0)
            from app.extensions import db

            db.session.add(stock)
        return stock

    def stocks_por_almacen(self, almacen_id):
        return (
            StockAlmacen.query.filter_by(almacen_id=almacen_id)
            .join(Insumo)
            .order_by(Insumo.nombre)
            .all()
        )

    def alertas(self):
        insumos = Insumo.query.filter_by(activo=True).all()
        return [insumo for insumo in insumos if insumo.bajo_minimo]


class MovimientoRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(MovimientoInventario)

    def movimientos(self, limite=100):
        return (
            MovimientoInventario.query.order_by(MovimientoInventario.fecha.desc())
            .limit(limite)
            .all()
        )

    def movimientos_entrada_pendientes(self):
        return (
            MovimientoInventario.query.filter_by(tipo="ENTRADA", estado_pago="PENDIENTE")
            .order_by(MovimientoInventario.fecha)
            .all()
        )


class MermaRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(Merma)

    def recientes(self, limite=100):
        return Merma.query.order_by(Merma.fecha.desc()).limit(limite).all()

    def en_rango(self, desde, hasta):
        return (
            Merma.query.filter(Merma.fecha >= desde, Merma.fecha <= hasta)
            .order_by(Merma.fecha)
            .all()
        )


class AvisoRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(AvisoFaltante)

    def pendientes(self):
        return (
            AvisoFaltante.query.filter_by(resuelto=False)
            .order_by(AvisoFaltante.creado)
            .all()
        )

    def pendiente_de(self, insumo_id):
        return (
            AvisoFaltante.query.filter_by(insumo_id=insumo_id, resuelto=False).first()
        )

    def historial(self, limite=50):
        return (
            AvisoFaltante.query.order_by(AvisoFaltante.creado.desc()).limit(limite).all()
        )
