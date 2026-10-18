from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.constants import Rol, Turno
from app.extensions import db
from app.security import role_required
from app.services.excepciones import ErrorDeNegocio
from app.services.inventario_service import InventarioService
from app.services.menu_service import MenuService

recetas_bp = Blueprint("recetas", __name__, url_prefix="/recetas")


@recetas_bp.route("/")
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def index():
    menu = MenuService()
    inventario = InventarioService()
    productos = menu.listar_productos()
    return render_template(
        "recetas/index.html",
        productos=productos,
        recetas={producto.id: menu.receta_de(producto.id) for producto in productos},
        insumos=inventario.insumos.activos(),
        almacenes=inventario.almacenes.todos_ordenados(),
        turnos=Turno.TODOS,
    )


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
            almacen_consumo_id=request.form.get("almacen_consumo_id", type=int),
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
