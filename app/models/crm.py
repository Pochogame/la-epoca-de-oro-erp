from datetime import datetime

from app.extensions import db


class Cliente(db.Model):
    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    telefono = db.Column(db.String(30), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), default="")
    cumpleanos = db.Column(db.Date)
    notas = db.Column(db.Text, default="")
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.now)

    ventas = db.relationship("Venta", back_populates="cliente")

    @property
    def telefono_limpio(self):
        return "".join(caracter for caracter in (self.telefono or "") if caracter.isdigit())

    def __repr__(self):
        return f"<Cliente {self.nombre} {self.telefono}>"
