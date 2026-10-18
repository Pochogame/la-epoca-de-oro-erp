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

    mesero = db.relationship("Usuario", back_populates="ventas")
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

    venta = db.relationship("Venta", back_populates="comanda")

    @property
    def mesero(self):
        return self.venta.mesero

    def __repr__(self):
        return f"<Comanda {self.folio} {self.estado}>"
