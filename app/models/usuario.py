from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from app.constants import Rol
from app.extensions import db


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(30), nullable=False, default=Rol.MESERO_POS)
    sueldo_diario = db.Column(db.Float, nullable=False, default=0.0)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    fecha_alta = db.Column(db.DateTime, default=datetime.now)

    asistencias = db.relationship(
        "Asistencia", back_populates="usuario", cascade="all, delete-orphan"
    )
    ventas = db.relationship("Venta", back_populates="mesero")

    def definir_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verificar_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def es_admin(self):
        return self.rol == Rol.ADMIN

    @property
    def es_chef(self):
        return self.rol == Rol.CHEF_SUPERVISOR

    @property
    def es_mesero(self):
        return self.rol == Rol.MESERO_POS

    @property
    def puede_ver_todo(self):
        return self.es_admin

    def tiene_rol(self, *roles):
        return self.rol in roles

    def __repr__(self):
        return f"<Usuario {self.username} ({self.rol})>"
