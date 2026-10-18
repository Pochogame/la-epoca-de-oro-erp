from datetime import datetime

from app.extensions import db


class Venta(db.Model):
    __tablename__ = "ventas"

    id = db.Column(db.Integer, primary_key=True)
    folio = db.Column(db.String(20), unique=True, nullable=False, index=True)
    fecha = db.Column(db.DateTime, default=datetime.now)
    turno = db.Column(db.String(10), nullable=False)
    tipo_orden = db.Column(db.String(10), nullable=False)
    metodo_pago = db.Column(db.String(20), nullable=False)
    total = db.Column(db.Float, nullable=False, default=0.0)
    costo_insumos = db.Column(db.Float, nullable=False, default=0.0)
    mesero_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    mesa_id = db.Column(db.Integer, db.ForeignKey("mesas.id"))
    cancelada = db.Column(db.Boolean, nullable=False, default=False)
    cancelada_en = db.Column(db.DateTime)
    motivo_cancelacion = db.Column(db.String(200), default="")

    mesero = db.relationship("Usuario", back_populates="ventas")
    mesa = db.relationship("Mesa", back_populates="ventas")
    detalles = db.relationship("VentaDetalle", back_populates="venta", cascade="all, delete-orphan")
    comanda = db.relationship("Comanda", back_populates="venta", uselist=False)

    @property
    def utilidad_bruta(self):
        return round(self.total - self.costo_insumos, 2)

    def __repr__(self):
        return f"<Venta {self.folio} ${self.total:.2f}>"


class VentaDetalle(db.Model):
    __tablename__ = "venta_detalles"

    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey("ventas.id"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    producto_nombre = db.Column(db.String(120), nullable=False)
    guisado = db.Column(db.String(60), default="")
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    precio_unitario = db.Column(db.Float, nullable=False, default=0.0)
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    costo_linea = db.Column(db.Float, nullable=False, default=0.0)

    venta = db.relationship("Venta", back_populates="detalles")
    producto = db.relationship("Producto", back_populates="detalles")


class Comanda(db.Model):
    __tablename__ = "comandas"

    id = db.Column(db.Integer, primary_key=True)
    folio = db.Column(db.String(20), unique=True, nullable=False, index=True)
    venta_id = db.Column(db.Integer, db.ForeignKey("ventas.id"), unique=True, nullable=False)
    turno = db.Column(db.String(10), nullable=False)
    tipo_orden = db.Column(db.String(10), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="EN_PREPARACION")
    creada = db.Column(db.DateTime, default=datetime.now)
    lista_en = db.Column(db.DateTime)
    entregada_en = db.Column(db.DateTime)
    merma_en = db.Column(db.DateTime)
    motivo_merma = db.Column(db.String(200), default="")
    cerrada_en = db.Column(db.DateTime)
    cerrada_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))

    venta = db.relationship("Venta", back_populates="comanda")
    cerrada_por = db.relationship("Usuario")

    @property
    def mesero(self):
        return self.venta.mesero

    @property
    def es_merma(self):
        return self.estado == "MERMA"

    def __repr__(self):
        return f"<Comanda {self.folio} {self.estado}>"


class Mesa(db.Model):
    __tablename__ = "mesas"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, unique=True, nullable=False)
    zona = db.Column(db.String(40), nullable=False, default="Salón principal")
    estado = db.Column(db.String(15), nullable=False, default="LIBRE")
    nota = db.Column(db.String(120), default="")

    ventas = db.relationship("Venta", back_populates="mesa")

    @property
    def comandas_activas(self):
        return [
            venta.comanda
            for venta in self.ventas
            if not venta.cancelada
            and venta.comanda is not None
            and venta.comanda.estado in ("EN_PREPARACION", "LISTA")
        ]

    @property
    def ocupada(self):
        return bool(self.comandas_activas)

    def __repr__(self):
        return f"<Mesa {self.numero} {self.estado}>"
