from app.models.ventas import Comanda, Venta, VentaDetalle
from app.repositories.base import RepositorioBase


class VentaRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(Venta)

    def siguiente_folio(self):
        ultimo = Venta.query.order_by(Venta.id.desc()).first()
        numero = (ultimo.id + 1) if ultimo else 1
        return f"VTA-{numero:05d}"

    def en_rango(self, desde, hasta):
        return Venta.query.filter(Venta.fecha >= desde, Venta.fecha <= hasta).order_by(Venta.fecha).all()

    def recientes(self, limite=50):
        return Venta.query.order_by(Venta.fecha.desc()).limit(limite).all()

    def del_mesero(self, mesero_id, limite=30):
        return (
            Venta.query.filter_by(mesero_id=mesero_id)
            .order_by(Venta.fecha.desc())
            .limit(limite)
            .all()
        )


class ComandaRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(Comanda)

    def siguiente_folio(self):
        ultima = Comanda.query.order_by(Comanda.id.desc()).first()
        numero = (ultima.id + 1) if ultima else 1
        return f"CMD-{numero:03d}"

    def activas(self):
        return (
            Comanda.query.filter(Comanda.estado.in_(("EN_PREPARACION", "LISTA")))
            .order_by(Comanda.creada)
            .all()
        )

    def historial(self, limite=50):
        return Comanda.query.order_by(Comanda.creada.desc()).limit(limite).all()
