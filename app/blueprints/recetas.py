from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.constants import Rol, Turno
from app.extensions import db
from app.models.menu import ProductoVariante
from app.security import role_required
from app.services.excepciones import ErrorDeNegocio
from app.services.inventario_service import InventarioService
from app.services.menu_service import ORDEN_CATEGORIAS, MenuService

recetas_bp = Blueprint("recetas", __name__, url_prefix="/recetas")


@recetas_bp.route("/")
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def index():
    menu = MenuService()
    inventario = InventarioService()
    productos = menu.listar_productos()

    recetas = {}
    for producto in productos:
        lineas = []
        for linea in menu.receta_de(producto.id):
            stock = inventario.stock_de(linea.insumo_id, producto.almacen_consumo_id)
            if stock <= 0:
                estado = "AGOTADO"
            elif linea.insumo.bajo_minimo:
                estado = "BAJO"
            else:
                estado = "OK"
            lineas.append({"linea": linea, "stock": stock, "estado": estado})
        recetas[producto.id] = lineas

    return render_template(
        "recetas/index.html",
        productos=productos,
        recetas=recetas,
        insumos=inventario.insumos.activos(),
        turnos=Turno.TODOS,
        categorias=ORDEN_CATEGORIAS,
    )


@recetas_bp.route("/producto/<int:producto_id>/editar", methods=["GET", "POST"])
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def editar_producto(producto_id):
    menu = MenuService()
    producto = menu.productos.obtener(producto_id)
    if producto is None:
        abort(404)
    if request.method == "POST":
        try:
            menu.actualizar_producto(
                producto_id=producto.id,
                codigo=request.form.get("codigo", ""),
                nombre=request.form.get("nombre", ""),
                categoria=request.form.get("categoria", ""),
                precio=request.form.get("precio", type=float),
                turno=request.form.get("turno", ""),
                requiere_guisado=request.form.get("requiere_guisado") == "on",
                activo=request.form.get("activo") == "on",
            )
        except ErrorDeNegocio as error:
            db.session.rollback()
            flash(error.mensaje, "error")
        else:
            flash("Producto actualizado.", "exito")
            return redirect(url_for("recetas.editar_producto", producto_id=producto.id))
    return render_template(
        "recetas/editar.html",
        producto=producto,
        turnos=Turno.TODOS,
        categorias=ORDEN_CATEGORIAS,
    )


@recetas_bp.route("/producto/<int:producto_id>/variante", methods=["POST"])
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def crear_variante(producto_id):
    try:
        MenuService().crear_variante(
            producto_id=producto_id,
            nombre=request.form.get("nombre", ""),
            precio=request.form.get("precio", type=float),
            factor_receta=request.form.get("factor_receta", type=float) or 1.0,
            activo=request.form.get("activo", "on") == "on",
        )
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        flash("Tamaño agregado al producto.", "exito")
    return redirect(url_for("recetas.editar_producto", producto_id=producto_id))


@recetas_bp.route("/variante/<int:variante_id>/editar", methods=["POST"])
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def editar_variante(variante_id):
    menu = MenuService()
    variante = db.session.get(ProductoVariante, variante_id)
    if variante is None:
        abort(404)
    try:
        menu.actualizar_variante(
            variante_id=variante.id,
            nombre=request.form.get("nombre", ""),
            precio=request.form.get("precio", type=float),
            factor_receta=request.form.get("factor_receta", type=float) or 1.0,
            activo=request.form.get("activo") == "on",
        )
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        flash("Tamaño actualizado.", "exito")
    return redirect(url_for("recetas.editar_producto", producto_id=variante.producto_id))


@recetas_bp.route("/producto", methods=["POST"])
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def crear_producto():
    try:
        MenuService().crear_producto(
            codigo=request.form.get("codigo", ""),
            nombre=request.form.get("nombre", ""),
            categoria=request.form.get("categoria", ""),
            precio=request.form.get("precio", type=float),
            turno=request.form.get("turno", ""),
            requiere_guisado=request.form.get("requiere_guisado") == "on",
        )
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        flash("Producto agregado al menú.", "exito")
    return redirect(url_for("recetas.index"))


@recetas_bp.route("/ingrediente", methods=["POST"])
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def agregar_ingrediente():
    try:
        MenuService().agregar_ingrediente(
            producto_id=request.form.get("producto_id", type=int),
            insumo_id=request.form.get("insumo_id", type=int),
            cantidad=request.form.get("cantidad", type=float),
        )
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        flash("Receta actualizada.", "exito")
    return redirect(url_for("recetas.index"))


@recetas_bp.route("/ingrediente/<int:linea_id>/eliminar", methods=["POST"])
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def eliminar_ingrediente(linea_id):
    try:
        MenuService().eliminar_ingrediente(linea_id)
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        flash("Ingrediente eliminado de la receta.", "exito")
    return redirect(url_for("recetas.index"))
