from flask import Blueprint, flash, redirect, render_template, url_for

from app.constants import Rol
from app.extensions import db
from app.security import role_required
from app.services.excepciones import ErrorDeNegocio
from app.services.venta_service import VentaService

cocina_bp = Blueprint("cocina", __name__, url_prefix="/cocina")


@cocina_bp.route("/")
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def index():
    ventas = VentaService()
    return render_template(
        "cocina/index.html",
        comandas=ventas.comandas_activas(),
        historial=ventas.historial_comandas(10),
    )


@cocina_bp.route("/comanda/<int:comanda_id>/listo", methods=["POST"])
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def marcar_listo(comanda_id):
    try:
        VentaService().marcar_comanda_lista(comanda_id)
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        flash(f"Comanda marcada como lista para entregar.", "exito")
    return redirect(url_for("cocina.index"))


@cocina_bp.route("/comanda/<int:comanda_id>/entregar", methods=["POST"])
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def despachar(comanda_id):
    try:
        VentaService().marcar_comanda_entregada(comanda_id)
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        flash("Comanda despachada y retirada de la pantalla de cocina.", "exito")
    return redirect(url_for("cocina.index"))
