from datetime import datetime

from app.constants import Turno
from app.extensions import db


class Asistencia(db.Model):
    __tablename__ = "asistencias"
    __table_args__ = (db.UniqueConstraint("usuario_id", "fecha", name="uq_asistencia_usuario_fecha"),)

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    fecha = db.Column(db.Date, nullable=False, default=lambda: datetime.now().date())
    hora_entrada = db.Column(db.Time)
    hora_salida = db.Column(db.Time)
    estado = db.Column(db.String(15), nullable=False, default="PRESENTE")

    usuario = db.relationship("Usuario", back_populates="asistencias")

    @property
    def horas_trabajadas(self):
        if not self.hora_entrada or not self.hora_salida:
            return 0.0
        entrada = datetime.combine(self.fecha, self.hora_entrada)
        salida = datetime.combine(self.fecha, self.hora_salida)
        return round((salida - entrada).total_seconds() / 3600, 2)

    @property
    def turno(self):
        if not self.hora_entrada:
            return Turno.MANANA
        return Turno.MANANA if self.hora_entrada.hour < 15 else Turno.TARDE


class NominaPago(db.Model):
    __tablename__ = "nomina_pagos"

    id = db.Column(db.Integer, primary_key=True)
    desde = db.Column(db.Date, nullable=False)
    hasta = db.Column(db.Date, nullable=False)
    total = db.Column(db.Float, nullable=False, default=0.0)
    detalle_json = db.Column(db.Text, default="[]")
    fecha_pago = db.Column(db.DateTime, default=datetime.now)
    gasto_id = db.Column(db.Integer, db.ForeignKey("gastos_operativos.id"))

    gasto = db.relationship("GastoOperativo")

    def __repr__(self):
        return f"<NominaPago {self.desde}->{self.hasta} ${self.total:.2f}>"
