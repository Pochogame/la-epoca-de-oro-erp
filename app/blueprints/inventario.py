from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app.constants import MOTIVOS_MERMA, EstadoPago, Rol
from app.extensions import db
from app.security import role_required
from app.services.excepciones import ErrorDeNegocio
from app.services.inventario_service import InventarioService

inventario_bp = Blueprint("inventario", __name__, url_prefix="/inventario")


def _servicio():
    return InventarioService()


@inventario_bp.route("/")
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def index():
    servicio = _servicio()
    return render_template(
        "inventario/index.html",
        panel=servicio.panel_almacenes(),
        alertas=servicio.alertas(),
        movimientos=servicio.movimientos(15),
    )


@inventario_bp.route("/entrada", methods=["GET", "POST"])
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def entrada():
    servicio = _servicio()
    if request.method == "POST":
        try:
            servicio.registrar_entrada(
                insumo_id=request.form.get("insumo_id", type=int),
                cantidad=request.form.get("cantidad", type=float),
                costo_unitario=request.form.get("costo_unitario", type=float),
                almacen_destino_id=servicio.principal().id,
                usuario_id=g.usuario.id,
                estado_pago=request.form.get("estado_pago", EstadoPago.PAGADO),
                referencia=request.form.get("referencia", ""),
            )
        except ErrorDeNegocio as error:
            db.session.rollback()
            flash(error.mensaje, "error")
        else:
            flash("Entrada de insumos registrada correctamente.", "exito")
            return redirect(url_for("inventario.index"))

    return render_template(
        "inventario/entrada.html",
        insumos=servicio.insumos.activos(),
    )


@inventario_bp.route("/merma", methods=["GET", "POST"])
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def merma():
    servicio = _servicio()
    if request.method == "POST":
        try:
            servicio.registrar_merma(
                insumo_id=request.form.get("insumo_id", type=int),
                almacen_id=servicio.principal().id,
                cantidad=request.form.get("cantidad", type=float),
                motivo=request.form.get("motivo", ""),
                comentario=request.form.get("comentario", ""),
                usuario_id=g.usuario.id,
            )
        except ErrorDeNegocio as error:
            db.session.rollback()
            flash(error.mensaje, "error")
        else:
            flash("Merma registrada y descontada del inventario.", "exito")
            return redirect(url_for("inventario.merma"))

    return render_template(
        "inventario/mermas.html",
        insumos=servicio.insumos.activos(),
        motivos=MOTIVOS_MERMA,
        historial=servicio.mermas.recientes(30),
    )


@inventario_bp.route("/insumos", methods=["GET", "POST"])
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def insumos():
    servicio = _servicio()
    if request.method == "POST":
        try:
            servicio.crear_insumo(
                codigo=request.form.get("codigo", ""),
                nombre=request.form.get("nombre", ""),
                unidad=request.form.get("unidad", "kg"),
                costo_unitario=request.form.get("costo_unitario", type=float),
                stock_minimo=request.form.get("stock_minimo", type=float),
            )
        except ErrorDeNegocio as error:
            db.session.rollback()
            flash(error.mensaje, "error")
        else:
            flash("Insumo registrado en el catálogo.", "exito")
            return redirect(url_for("inventario.insumos"))

    return render_template("inventario/insumos.html", insumos=servicio.insumos.activos())


@inventario_bp.route("/movimientos")
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def movimientos():
    servicio = _servicio()
    return render_template(
        "inventario/movimientos.html", movimientos=servicio.movimientos(200)
    )
