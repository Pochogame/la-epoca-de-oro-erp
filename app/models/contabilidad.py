from datetime import datetime

from app.extensions import db


class CuentaContable(db.Model):
    __tablename__ = "cuentas_contables"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(10), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(120), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)

    lineas = db.relationship("AsientoLinea", back_populates="cuenta")

    def __repr__(self):
        return f"<Cuenta {self.codigo} {self.nombre}>"


class Asiento(db.Model):
    __tablename__ = "asientos"

    id = db.Column(db.Integer, primary_key=True)
    folio = db.Column(db.String(20), unique=True, nullable=False, index=True)
    fecha = db.Column(db.DateTime, default=datetime.now)
    concepto = db.Column(db.String(200), nullable=False)
    origen = db.Column(db.String(30), nullable=False, default="MANUAL")
    referencia = db.Column(db.String(50), default="")

    lineas = db.relationship("AsientoLinea", back_populates="asiento", cascade="all, delete-orphan")

    @property
    def total_debe(self):
        return round(sum(linea.debe for linea in self.lineas), 2)

    @property
    def total_haber(self):
        return round(sum(linea.haber for linea in self.lineas), 2)

    def __repr__(self):
        return f"<Asiento {self.folio} {self.concepto}>"


class AsientoLinea(db.Model):
    __tablename__ = "asiento_lineas"

    id = db.Column(db.Integer, primary_key=True)
    asiento_id = db.Column(db.Integer, db.ForeignKey("asientos.id"), nullable=False)
    cuenta_id = db.Column(db.Integer, db.ForeignKey("cuentas_contables.id"), nullable=False)
    debe = db.Column(db.Float, nullable=False, default=0.0)
    haber = db.Column(db.Float, nullable=False, default=0.0)

    asiento = db.relationship("Asiento", back_populates="lineas")
    cuenta = db.relationship("CuentaContable", back_populates="lineas")


class GastoOperativo(db.Model):
    __tablename__ = "gastos_operativos"

    id = db.Column(db.Integer, primary_key=True)
    categoria = db.Column(db.String(30), nullable=False)
    descripcion = db.Column(db.String(200), nullable=False)
    monto = db.Column(db.Float, nullable=False, default=0.0)
    fecha = db.Column(db.DateTime, default=datetime.now)
    estado = db.Column(db.String(15), nullable=False, default="PAGADO")
    fecha_pago = db.Column(db.DateTime)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"))

    usuario = db.relationship("Usuario")

    def __repr__(self):
        return f"<Gasto {self.categoria} ${self.monto:.2f}>"
