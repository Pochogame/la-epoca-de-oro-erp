from app.models.usuario import Usuario
from app.repositories.base import RepositorioBase


class UsuarioRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(Usuario)

    def por_username(self, username):
        return Usuario.query.filter_by(username=username.strip().lower()).first()

    def por_email(self, email):
        return Usuario.query.filter_by(email=email.strip().lower()).first()

    def activos(self):
        return Usuario.query.filter_by(activo=True).order_by(Usuario.nombre).all()

    def todos_ordenados(self):
        return Usuario.query.order_by(Usuario.rol, Usuario.nombre).all()

    def empleados(self):
        return Usuario.query.filter_by(activo=True).order_by(Usuario.rol.desc(), Usuario.nombre).all()
