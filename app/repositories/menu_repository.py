from app.models.menu import Producto, RecetaIngrediente
from app.repositories.base import RepositorioBase


class ProductoRepositorio(RepositorioBase):
    def __init__(self):
        super().__init__(Producto)

    def por_codigo(self, codigo):
        return Producto.query.filter_by(codigo=codigo).first()

    def activos(self):
        return Producto.query.filter_by(activo=True).order_by(Producto.categoria, Producto.nombre).all()

    def activos_de_turno(self, turno):
        return (
            Producto.query.filter(Producto.activo.is_(True), Producto.turno.in_((turno, "AMBOS")))
            .order_by(Producto.categoria, Producto.nombre)
            .all()
        )

    def receta_de(self, producto_id):
        return (
            RecetaIngrediente.query.filter_by(producto_id=producto_id)
            .join(RecetaIngrediente.insumo)
            .order_by(RecetaIngrediente.id)
            .all()
        )

    def linea_receta(self, producto_id, insumo_id):
        return RecetaIngrediente.query.filter_by(
            producto_id=producto_id, insumo_id=insumo_id
        ).first()
