from app.extensions import db
from app.models.ventas import (
    CancelacionPlatillo,
    Comanda,
    CuentaMesa,
    Mesa,
    Venta,
    VentaDetalle,
)
from app.repositories.base import RepositorioBase


class VentaRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(Venta)

    def siguiente_folio(self):
        ultimo = Venta.query.order_by(Venta.id.desc()).first()
        numero = (ultimo.id + 1) if ultimo else 1
        return f"VTA-{numero:05d}"

    def en_rango(self, desde, hasta):
        return (
            Venta.query.filter(
                Venta.fecha >= desde,
                Venta.fecha <= hasta,
                Venta.cancelada.is_(False),
                Venta.cobrada_en.isnot(None),
            )
            .order_by(Venta.fecha)
            .all()
        )

    def recientes(self, limite=50):
        return (
            Venta.query.filter(
                Venta.cancelada.is_(False), Venta.cobrada_en.isnot(None)
            )
            .order_by(Venta.fecha.desc())
            .limit(limite)
            .all()
        )

    def del_mesero(self, mesero_id, limite=30):
        return (
            Venta.query.filter_by(mesero_id=mesero_id, cancelada=False)
            .order_by(Venta.fecha.desc())
            .limit(limite)
            .all()
        )


class CuentaMesaRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(CuentaMesa)

    def siguiente_folio(self):
        ultima = CuentaMesa.query.order_by(CuentaMesa.id.desc()).first()
        numero = (ultima.id + 1) if ultima else 1
        return f"CTA-{numero:05d}"

    def abierta_de(self, mesa_id):
        return CuentaMesa.query.filter_by(mesa_id=mesa_id, cerrada_en=None).first()

    def abiertas(self):
        return (
            CuentaMesa.query.filter(CuentaMesa.cerrada_en.is_(None))
            .order_by(CuentaMesa.abierta_en)
            .all()
        )


class CancelacionRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(CancelacionPlatillo)

    def pendientes(self):
        return (
            CancelacionPlatillo.query.filter(CancelacionPlatillo.atendida_en.is_(None))
            .order_by(CancelacionPlatillo.creada)
            .all()
        )

    def de_detalle(self, detalle_id):
        return CancelacionPlatillo.query.filter_by(detalle_id=detalle_id).first()


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

    def pendientes_de_mesero(self, mesero_id, limite=30):
        return (
            Comanda.query.join(Venta)
            .filter(
                Venta.mesero_id == mesero_id,
                Venta.cancelada.is_(False),
                Comanda.cerrada_en.is_(None),
            )
            .order_by(Comanda.estado.desc(), Comanda.creada.desc())
            .limit(limite)
            .all()
        )

    def historial(self, limite=50):
        return Comanda.query.order_by(Comanda.creada.desc()).limit(limite).all()

    def mermas_en_rango(self, desde, hasta):
        return (
            Comanda.query.join(Venta)
            .filter(
                Comanda.estado == "MERMA",
                Venta.fecha >= desde,
                Venta.fecha <= hasta,
            )
            .order_by(Venta.fecha)
            .all()
        )


class MesaRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(Mesa)

    def todas(self):
        return Mesa.query.order_by(Mesa.numero).all()

    def por_numero(self, numero):
        return Mesa.query.filter_by(numero=numero).first()

    def por_zona(self):
        zonas = {}
        for mesa in self.todas():
            zonas.setdefault(mesa.zona, []).append(mesa)
        return zonas


class VentaDetalleRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(VentaDetalle)
