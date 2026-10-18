from datetime import datetime

from app.constants import HORA_CORTE_TURNO, GUISADOS, Turno
from app.extensions import db
from app.models.menu import Producto, RecetaIngrediente
from app.repositories.inventario_repository import InsumoRepositorio
from app.repositories.menu_repository import ProductoRepositorio
from app.services.excepciones import DatosInvalidosError

ORDEN_CATEGORIAS = (
    "Bebidas Calientes",
    "Barra Fría (Frappés y Smoothies)",
    "Panadería y Repostería",
    "Almuerzos Caseros",
    "Platillos de Cuchara",
    "Antojitos (Tacos y Tortas)",
    "Refrescos",
    "Aguas Frescas",
)


class MenuService:
    def __init__(self, productos=None, insumos=None, almacenes=None):
        self.productos = productos or ProductoRepositorio()
        self.insumos = insumos or InsumoRepositorio()
        self.almacenes = almacenes

    def turno_sugerido(self):
        return Turno.MANANA if datetime.now().hour < HORA_CORTE_TURNO else Turno.TARDE

    def catalogo_por_turno(self, turno):
        productos = self.productos.activos_de_turno(turno)
        agrupado = {}
        for producto in productos:
            agrupado.setdefault(producto.categoria, []).append(producto)
        return [
            {"categoria": categoria, "productos": agrupado[categoria]}
            for categoria in sorted(
                agrupado,
                key=lambda nombre: ORDEN_CATEGORIAS.index(nombre)
                if nombre in ORDEN_CATEGORIAS
                else 99,
            )
        ]

    def listar_productos(self):
        return self.productos.activos()

    def lista_guisados(self):
        return GUISADOS

    def crear_producto(
        self,
        codigo,
        nombre,
        categoria,
        precio,
        turno,
        requiere_guisado,
        almacen_consumo_id,
    ):
        codigo = (codigo or "").strip().upper()
        nombre = (nombre or "").strip()
        categoria = (categoria or "").strip()
        if not codigo or not nombre or not categoria:
            raise DatosInvalidosError("Código, nombre y categoría son obligatorios.")
        if self.productos.por_codigo(codigo):
            raise DatosInvalidosError(f"Ya existe un producto con el código {codigo}.")
        if turno not in Turno.TODOS:
            raise DatosInvalidosError("El turno del producto no es válido.")
        if precio is None or float(precio) <= 0:
            raise DatosInvalidosError("El precio debe ser mayor a cero.")
        if almacen_consumo_id is None:
            raise DatosInvalidosError("Selecciona el almacén de consumo del producto.")

        producto = Producto(
            codigo=codigo,
            nombre=nombre,
            categoria=categoria,
            precio=round(float(precio), 2),
            turno=turno,
            requiere_guisado=bool(requiere_guisado),
            almacen_consumo_id=almacen_consumo_id,
        )
        self.productos.agregar(producto)
        db.session.commit()
        return producto

    def agregar_ingrediente(self, producto_id, insumo_id, cantidad):
        producto = self.productos.obtener(producto_id)
        if producto is None:
            raise DatosInvalidosError("El producto indicado no existe.")
        insumo = self.insumos.obtener(insumo_id)
        if insumo is None:
            raise DatosInvalidosError("El insumo indicado no existe.")
        if cantidad is None or float(cantidad) <= 0:
            raise DatosInvalidosError("La cantidad del ingrediente debe ser mayor a cero.")

        linea = self.productos.linea_receta(producto.id, insumo.id)
        if linea is None:
            linea = RecetaIngrediente(
                producto_id=producto.id, insumo_id=insumo.id, cantidad=round(float(cantidad), 4)
            )
            self.productos.agregar(linea)
        else:
            linea.cantidad = round(float(cantidad), 4)
        db.session.commit()
        return linea

    def eliminar_ingrediente(self, linea_id):
        linea = db.session.get(RecetaIngrediente, linea_id)
        if linea is None:
            raise DatosInvalidosError("El ingrediente indicado no existe en la receta.")
        self.productos.eliminar(linea)
        db.session.commit()

    def receta_de(self, producto_id):
        return self.productos.receta_de(producto_id)
