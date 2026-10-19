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
    cuenta_id = db.Column(db.Integer, db.ForeignKey("cuentas_mesa.id"))
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"))
    cobrada_en = db.Column(db.DateTime)
    cancelada = db.Column(db.Boolean, nullable=False, default=False)
    cancelada_en = db.Column(db.DateTime)
    motivo_cancelacion = db.Column(db.String(200), default="")

    mesero = db.relationship("Usuario", back_populates="ventas")
    mesa = db.relationship("Mesa", back_populates="ventas")
    cuenta = db.relationship("CuentaMesa", back_populates="ventas")
    cliente = db.relationship("Cliente", back_populates="ventas")
    detalles = db.relationship("VentaDetalle", back_populates="venta", cascade="all, delete-orphan")
    comanda = db.relationship("Comanda", back_populates="venta", uselist=False)

    @property
    def utilidad_bruta(self):
        return round(self.total - self.costo_insumos, 2)

    @property
    def cobrada(self):
        return self.cobrada_en is not None

    @property
    def por_cobrar(self):
        return self.cuenta_id is not None and self.cobrada_en is None

    def __repr__(self):
        return f"<Venta {self.folio} ${self.total:.2f}>"


class CuentaMesa(db.Model):
    __tablename__ = "cuentas_mesa"

    id = db.Column(db.Integer, primary_key=True)
    folio = db.Column(db.String(20), unique=True, nullable=False, index=True)
    mesa_id = db.Column(db.Integer, db.ForeignKey("mesas.id"), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"))
    abierta_en = db.Column(db.DateTime, default=datetime.now)
    abierta_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    cerrada_en = db.Column(db.DateTime)
    cerrada_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    metodo_pago = db.Column(db.String(20), default="")

    mesa = db.relationship("Mesa", back_populates="cuentas")
    cliente = db.relationship("Cliente")
    abierta_por = db.relationship("Usuario", foreign_keys=[abierta_por_id])
    cerrada_por = db.relationship("Usuario", foreign_keys=[cerrada_por_id])
    ventas = db.relationship("Venta", back_populates="cuenta", order_by="Venta.id")

    @property
    def abierta(self):
        return self.cerrada_en is None

    @property
    def ventas_vigentes(self):
        return [venta for venta in self.ventas if not venta.cancelada]

    @property
    def total(self):
        return round(sum(venta.total for venta in self.ventas_vigentes), 2)

    @property
    def rondas(self):
        return len(self.ventas_vigentes)

    def __repr__(self):
        return f"<CuentaMesa {self.folio} mesa={self.mesa_id}>"


class VentaDetalle(db.Model):
    __tablename__ = "venta_detalles"

    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey("ventas.id"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    producto_nombre = db.Column(db.String(120), nullable=False)
    variante_id = db.Column(db.Integer, db.ForeignKey("producto_variantes.id"))
    variante_nombre = db.Column(db.String(40), default="")
    guisado = db.Column(db.String(60), default="")
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    precio_unitario = db.Column(db.Float, nullable=False, default=0.0)
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    costo_linea = db.Column(db.Float, nullable=False, default=0.0)
    cancelado = db.Column(db.Boolean, nullable=False, default=False)
    cancelado_en = db.Column(db.DateTime)
    motivo_cancelacion = db.Column(db.String(200), default="")
    cancelado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    autorizado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))

    venta = db.relationship("Venta", back_populates="detalles")
    producto = db.relationship("Producto", back_populates="detalles")
    variante = db.relationship("ProductoVariante", back_populates="detalles")
    cancelado_por = db.relationship("Usuario", foreign_keys=[cancelado_por_id])
    autorizado_por = db.relationship("Usuario", foreign_keys=[autorizado_por_id])


class CancelacionPlatillo(db.Model):
    __tablename__ = "cancelaciones_platillo"

    id = db.Column(db.Integer, primary_key=True)
    detalle_id = db.Column(
        db.Integer, db.ForeignKey("venta_detalles.id"), nullable=False, unique=True
    )
    comanda_id = db.Column(db.Integer, db.ForeignKey("comandas.id"), nullable=False)
    motivo = db.Column(db.String(200), default="")
    creada = db.Column(db.DateTime, default=datetime.now)
    cancelado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    autorizado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))
    atendida_en = db.Column(db.DateTime)
    atendida_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))

    detalle = db.relationship("VentaDetalle")
    comanda = db.relationship("Comanda")
    cancelado_por = db.relationship("Usuario", foreign_keys=[cancelado_por_id])
    autorizado_por = db.relationship("Usuario", foreign_keys=[autorizado_por_id])
    atendida_por = db.relationship("Usuario", foreign_keys=[atendida_por_id])

    @property
    def pendiente(self):
        return self.atendida_en is None

    def __repr__(self):
        return f"<CancelacionPlatillo detalle={self.detalle_id}>"


class Comanda(db.Model):
    __tablename__ = "comandas"

    id = db.Column(db.Integer, primary_key=True)
    folio = db.Column(db.String(20), unique=True, nullable=False, index=True)
    venta_id = db.Column(db.Integer, db.ForeignKey("ventas.id"), unique=True, nullable=False)
    turno = db.Column(db.String(10), nullable=False)
    tipo_orden = db.Column(db.String(10), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="EN_PREPARACION")
    ronda = db.Column(db.Integer, nullable=False, default=1)
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
    cuentas = db.relationship("CuentaMesa", back_populates="mesa", order_by="CuentaMesa.id")

    @property
    def cuenta_abierta(self):
        for cuenta in self.cuentas:
            if cuenta.abierta:
                return cuenta
        return None

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
