from app.models.rrhh import Asistencia, NominaPago
from app.repositories.base import RepositorioBase


class AsistenciaRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(Asistencia)

    def del_dia(self, usuario_id, fecha):
        return Asistencia.query.filter_by(usuario_id=usuario_id, fecha=fecha).first()

    def en_rango(self, desde, hasta, usuario_id=None):
        consulta = Asistencia.query.filter(Asistencia.fecha >= desde, Asistencia.fecha <= hasta)
        if usuario_id:
            consulta = consulta.filter_by(usuario_id=usuario_id)
        return consulta.order_by(Asistencia.fecha.desc()).all()

    def recientes(self, limite=50):
        return Asistencia.query.order_by(Asistencia.fecha.desc()).limit(limite).all()


class NominaRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(NominaPago)

    def del_periodo(self, desde, hasta):
        return NominaPago.query.filter_by(desde=desde, hasta=hasta).first()

    def historial(self):
        return NominaPago.query.order_by(NominaPago.fecha_pago.desc()).all()
