from datetime import datetime

from app.extensions import db


class Almacen(db.Model):
    __tablename__ = "almacenes"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(80), nullable=False)
    descripcion = db.Column(db.String(200), default="")

    stocks = db.relationship("StockAlmacen", back_populates="almacen", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Almacen {self.codigo}>"


class Insumo(db.Model):
    __tablename__ = "insumos"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(120), nullable=False)
    unidad = db.Column(db.String(10), nullable=False, default="kg")
    costo_unitario = db.Column(db.Float, nullable=False, default=0.0)
    stock_minimo = db.Column(db.Float, nullable=False, default=0.0)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    stocks = db.relationship("StockAlmacen", back_populates="insumo", cascade="all, delete-orphan")
    recetas = db.relationship("RecetaIngrediente", back_populates="insumo")

    @property
    def cantidad_total(self):
        return round(sum(stock.cantidad for stock in self.stocks), 4)

    @property
    def bajo_minimo(self):
        return self.cantidad_total < self.stock_minimo

    def stock_en(self, almacen_id):
        for stock in self.stocks:
            if stock.almacen_id == almacen_id:
                return stock
        return None

    def __repr__(self):
        return f"<Insumo {self.codigo} {self.nombre}>"


class StockAlmacen(db.Model):
    __tablename__ = "stock_almacen"
    __table_args__ = (db.UniqueConstraint("insumo_id", "almacen_id", name="uq_stock_insumo_almacen"),)

    id = db.Column(db.Integer, primary_key=True)
    insumo_id = db.Column(db.Integer, db.ForeignKey("insumos.id"), nullable=False)
    almacen_id = db.Column(db.Integer, db.ForeignKey("almacenes.id"), nullable=False)
    cantidad = db.Column(db.Float, nullable=False, default=0.0)

    insumo = db.relationship("Insumo", back_populates="stocks")
    almacen = db.relationship("Almacen", back_populates="stocks")


class MovimientoInventario(db.Model):
    __tablename__ = "movimientos_inventario"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(30), nullable=False)
    insumo_id = db.Column(db.Integer, db.ForeignKey("insumos.id"), nullable=False)
    almacen_origen_id = db.Column(db.Integer, db.ForeignKey("almacenes.id"))
    almacen_destino_id = db.Column(db.Integer, db.ForeignKey("almacenes.id"))
    cantidad = db.Column(db.Float, nullable=False)
    costo_unitario = db.Column(db.Float, nullable=False, default=0.0)
    costo_total = db.Column(db.Float, nullable=False, default=0.0)
    motivo = db.Column(db.String(200), default="")
    referencia = db.Column(db.String(50), default="")
    estado_pago = db.Column(db.String(15), default="NO_APLICA")
    fecha = db.Column(db.DateTime, default=datetime.now)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))

    insumo = db.relationship("Insumo")
    almacen_origen = db.relationship("Almacen", foreign_keys=[almacen_origen_id])
    almacen_destino = db.relationship("Almacen", foreign_keys=[almacen_destino_id])
    usuario = db.relationship("Usuario")


class Merma(db.Model):
    __tablename__ = "mermas"

    id = db.Column(db.Integer, primary_key=True)
    insumo_id = db.Column(db.Integer, db.ForeignKey("insumos.id"), nullable=False)
    almacen_id = db.Column(db.Integer, db.ForeignKey("almacenes.id"), nullable=False)
    cantidad = db.Column(db.Float, nullable=False)
    motivo = db.Column(db.String(100), nullable=False)
    comentario = db.Column(db.String(250), default="")
    costo_estimado = db.Column(db.Float, nullable=False, default=0.0)
    fecha = db.Column(db.DateTime, default=datetime.now)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))

    insumo = db.relationship("Insumo")
    almacen = db.relationship("Almacen")
    usuario = db.relationship("Usuario")


class AvisoFaltante(db.Model):
    __tablename__ = "avisos_faltantes"

    id = db.Column(db.Integer, primary_key=True)
    insumo_id = db.Column(db.Integer, db.ForeignKey("insumos.id"), nullable=False)
    almacen_id = db.Column(db.Integer, db.ForeignKey("almacenes.id"))
    comentario = db.Column(db.String(200), default="")
    creado = db.Column(db.DateTime, default=datetime.now)
    resuelto = db.Column(db.Boolean, nullable=False, default=False)
    resuelto_en = db.Column(db.DateTime)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    resuelto_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))

    insumo = db.relationship("Insumo")
    almacen = db.relationship("Almacen")
    usuario = db.relationship("Usuario", foreign_keys=[usuario_id])
    resuelto_por = db.relationship("Usuario", foreign_keys=[resuelto_por_id])
