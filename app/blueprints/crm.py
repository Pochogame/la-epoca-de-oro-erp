from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.constants import Rol
from app.extensions import db
from app.security import role_required
from app.services.crm_service import ClienteService
from app.services.excepciones import ErrorDeNegocio

crm_bp = Blueprint("crm", __name__, url_prefix="/crm")


@crm_bp.route("/")
@role_required(Rol.ADMIN)
def index():
    servicio = ClienteService()
    busqueda = request.args.get("q", "")
    return render_template(
        "crm/index.html",
        clientes=servicio.listar(busqueda),
        busqueda=busqueda,
    )


@crm_bp.route("/nuevo", methods=["GET", "POST"])
@role_required(Rol.ADMIN)
def nuevo():
    if request.method == "POST":
        try:
            cliente = ClienteService().crear(
                nombre=request.form.get("nombre", ""),
                telefono=request.form.get("telefono", ""),
                email=request.form.get("email", ""),
                cumpleanos=request.form.get("cumpleanos", ""),
                notas=request.form.get("notas", ""),
            )
        except ErrorDeNegocio as error:
            db.session.rollback()
            flash(error.mensaje, "error")
        else:
            flash("Cliente registrado en el CRM.", "exito")
            return redirect(url_for("crm.detalle", cliente_id=cliente.id))
    return render_template("crm/formulario.html", cliente=None)


@crm_bp.route("/<int:cliente_id>")
@role_required(Rol.ADMIN)
def detalle(cliente_id):
    metricas = ClienteService().metricas(cliente_id)
    if metricas is None:
        abort(404)
    return render_template("crm/detalle.html", **metricas)


@crm_bp.route("/<int:cliente_id>/editar", methods=["GET", "POST"])
@role_required(Rol.ADMIN)
def editar(cliente_id):
    servicio = ClienteService()
    cliente = servicio.obtener(cliente_id)
    if cliente is None:
        abort(404)
    if request.method == "POST":
        try:
            servicio.actualizar(
                cliente_id=cliente.id,
                nombre=request.form.get("nombre", ""),
                telefono=request.form.get("telefono", ""),
                email=request.form.get("email", ""),
                cumpleanos=request.form.get("cumpleanos", ""),
                notas=request.form.get("notas", ""),
                activo=request.form.get("activo") == "on",
            )
        except ErrorDeNegocio as error:
            db.session.rollback()
            flash(error.mensaje, "error")
        else:
            flash("Cliente actualizado.", "exito")
            return redirect(url_for("crm.detalle", cliente_id=cliente.id))
    return render_template("crm/formulario.html", cliente=cliente)
