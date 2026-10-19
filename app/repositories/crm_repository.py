from sqlalchemy import or_

from app.models.crm import Cliente
from app.repositories.base import RepositorioBase


class ClienteRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(Cliente)

    def por_telefono(self, telefono):
        return Cliente.query.filter_by(telefono=telefono).first()

    def activos(self):
        return Cliente.query.filter_by(activo=True).order_by(Cliente.nombre).all()

    def todos(self):
        return Cliente.query.order_by(Cliente.nombre).all()

    def buscar(self, texto):
        termino = (texto or "").strip()
        if not termino:
            return self.todos()
        patron = f"%{termino}%"
        condiciones = [
            Cliente.nombre.ilike(patron),
            Cliente.telefono.ilike(patron),
            Cliente.email.ilike(patron),
        ]
        digitos = "".join(caracter for caracter in termino if caracter.isdigit())
        if digitos and digitos != termino:
            condiciones.append(Cliente.telefono.ilike(f"%{digitos}%"))
        return (
            Cliente.query.filter(or_(*condiciones))
            .order_by(Cliente.nombre)
            .all()
        )
