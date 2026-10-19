from datetime import datetime

from app.constants import HORA_CORTE_TURNO, GUISADOS, Turno
from app.extensions import db
from app.models.menu import Producto, ProductoVariante, RecetaIngrediente
from app.repositories.inventario_repository import AlmacenRepositorio, InsumoRepositorio
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
        self.almacenes = almacenes or AlmacenRepositorio()

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
        almacen_consumo_id=None,
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
        principal = self.almacenes.principal()
        if almacen_consumo_id is None and principal is not None:
            almacen_consumo_id = principal.id
        if almacen_consumo_id is None:
            raise DatosInvalidosError("No hay un almacén principal configurado.")

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

    def actualizar_producto(
        self,
        producto_id,
        codigo,
        nombre,
        categoria,
        precio,
        turno,
        requiere_guisado,
        activo=True,
    ):
        producto = self.productos.obtener(producto_id)
        if producto is None:
            raise DatosInvalidosError("El producto indicado no existe.")
        codigo = (codigo or "").strip().upper()
        nombre = (nombre or "").strip()
        categoria = (categoria or "").strip()
        if not codigo or not nombre or not categoria:
            raise DatosInvalidosError("Código, nombre y categoría son obligatorios.")
        existente = self.productos.por_codigo(codigo)
        if existente is not None and existente.id != producto.id:
            raise DatosInvalidosError(f"Ya existe un producto con el código {codigo}.")
        if turno not in Turno.TODOS:
            raise DatosInvalidosError("El turno del producto no es válido.")
        if precio is None or float(precio) <= 0:
            raise DatosInvalidosError("El precio debe ser mayor a cero.")

        producto.codigo = codigo
        producto.nombre = nombre
        producto.categoria = categoria
        producto.precio = round(float(precio), 2)
        producto.turno = turno
        producto.requiere_guisado = bool(requiere_guisado)
        producto.activo = bool(activo)
        db.session.commit()
        return producto

    def crear_variante(self, producto_id, nombre, precio, factor_receta=1.0, activo=True):
        producto = self.productos.obtener(producto_id)
        if producto is None:
            raise DatosInvalidosError("El producto indicado no existe.")
        nombre = (nombre or "").strip()
        if not nombre:
            raise DatosInvalidosError("El nombre del tamaño es obligatorio.")
        if self.productos.variante_por_nombre(producto.id, nombre) is not None:
            raise DatosInvalidosError(f"Ya existe el tamaño {nombre} para este producto.")
        if precio is None or float(precio) <= 0:
            raise DatosInvalidosError("El precio del tamaño debe ser mayor a cero.")
        if factor_receta is None or float(factor_receta) <= 0:
            raise DatosInvalidosError("El factor de receta debe ser mayor a cero.")

        orden = max((variante.orden for variante in producto.variantes), default=-1) + 1
        variante = ProductoVariante(
            producto_id=producto.id,
            nombre=nombre,
            precio=round(float(precio), 2),
            factor_receta=round(float(factor_receta), 4),
            activo=bool(activo),
            orden=orden,
        )
        db.session.add(variante)
        db.session.commit()
        return variante

    def actualizar_variante(self, variante_id, nombre, precio, factor_receta, activo=True):
        variante = db.session.get(ProductoVariante, variante_id)
        if variante is None:
            raise DatosInvalidosError("El tamaño indicado no existe.")
        nombre = (nombre or "").strip()
        if not nombre:
            raise DatosInvalidosError("El nombre del tamaño es obligatorio.")
        existente = self.productos.variante_por_nombre(variante.producto_id, nombre)
        if existente is not None and existente.id != variante.id:
            raise DatosInvalidosError(f"Ya existe el tamaño {nombre} para este producto.")
        if precio is None or float(precio) <= 0:
            raise DatosInvalidosError("El precio del tamaño debe ser mayor a cero.")
        if factor_receta is None or float(factor_receta) <= 0:
            raise DatosInvalidosError("El factor de receta debe ser mayor a cero.")

        variante.nombre = nombre
        variante.precio = round(float(precio), 2)
        variante.factor_receta = round(float(factor_receta), 4)
        variante.activo = bool(activo)
        db.session.commit()
        return variante

    def variantes_de(self, producto_id, solo_activas=False):
        return self.productos.variantes_de(producto_id, solo_activas=solo_activas)

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
