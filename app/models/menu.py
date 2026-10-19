from app.extensions import db


class Producto(db.Model):
    __tablename__ = "productos"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(120), nullable=False)
    categoria = db.Column(db.String(60), nullable=False)
    precio = db.Column(db.Float, nullable=False, default=0.0)
    turno = db.Column(db.String(10), nullable=False, default="MANANA")
    requiere_guisado = db.Column(db.Boolean, nullable=False, default=False)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    almacen_consumo_id = db.Column(db.Integer, db.ForeignKey("almacenes.id"))

    almacen_consumo = db.relationship("Almacen")
    receta = db.relationship(
        "RecetaIngrediente", back_populates="producto", cascade="all, delete-orphan"
    )
    variantes = db.relationship(
        "ProductoVariante",
        back_populates="producto",
        cascade="all, delete-orphan",
        order_by="ProductoVariante.orden",
    )
    detalles = db.relationship("VentaDetalle", back_populates="producto")

    @property
    def disponible_turno(self):
        return self.turno in ("MANANA", "TARDE", "AMBOS")

    def aplica_turno(self, turno):
        return self.turno in (turno, "AMBOS")

    @property
    def variantes_activas(self):
        return [variante for variante in self.variantes if variante.activo]

    @property
    def tiene_variantes(self):
        return bool(self.variantes_activas)

    @property
    def precio_desde(self):
        precios = [variante.precio for variante in self.variantes_activas]
        return min(precios) if precios else self.precio

    @property
    def costo_receta(self):
        return round(sum(linea.costo for linea in self.receta), 4)

    def __repr__(self):
        return f"<Producto {self.codigo} {self.nombre}>"


class ProductoVariante(db.Model):
    __tablename__ = "producto_variantes"
    __table_args__ = (
        db.UniqueConstraint("producto_id", "nombre", name="uq_variante_producto_nombre"),
    )

    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    nombre = db.Column(db.String(40), nullable=False)
    precio = db.Column(db.Float, nullable=False, default=0.0)
    factor_receta = db.Column(db.Float, nullable=False, default=1.0)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    orden = db.Column(db.Integer, nullable=False, default=0)

    producto = db.relationship("Producto", back_populates="variantes")
    detalles = db.relationship("VentaDetalle", back_populates="variante")

    def __repr__(self):
        return f"<ProductoVariante {self.nombre} ${self.precio:.2f}>"


class RecetaIngrediente(db.Model):
    __tablename__ = "receta_ingredientes"
    __table_args__ = (
        db.UniqueConstraint("producto_id", "insumo_id", name="uq_receta_producto_insumo"),
    )

    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey("productos.id"), nullable=False)
    insumo_id = db.Column(db.Integer, db.ForeignKey("insumos.id"), nullable=False)
    cantidad = db.Column(db.Float, nullable=False, default=0.0)

    producto = db.relationship("Producto", back_populates="receta")
    insumo = db.relationship("Insumo", back_populates="recetas")

    @property
    def costo(self):
        return round(self.cantidad * self.insumo.costo_unitario, 4)
