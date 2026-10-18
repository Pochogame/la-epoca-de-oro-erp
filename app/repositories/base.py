from app.extensions import db


class RepositorioBase:
    def __init__(self, modelo):
        self.modelo = modelo

    def obtener(self, id_):
        return db.session.get(self.modelo, id_)

    def obtener_o_none(self, id_):
        return db.session.get(self.modelo, id_)

    def listar(self):
        return self.modelo.query.order_by(self.modelo.id).all()

    def agregar(self, entidad):
        db.session.add(entidad)
        return entidad

    def eliminar(self, entidad):
        db.session.delete(entidad)

    def contar(self):
        return self.modelo.query.count()
