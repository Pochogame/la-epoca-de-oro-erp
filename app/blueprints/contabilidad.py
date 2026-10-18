from datetime import date

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app.constants import CATEGORIAS_GASTO, EstadoPago, Rol
from app.extensions import db
from app.security import role_required
from app.services.contabilidad_service import ContabilidadService
from app.services.excepciones import ErrorDeNegocio
from app.utilidades import (
    inicio_mes_actual,
    parse_fecha,
    rango_fechas,
)

contabilidad_bp = Blueprint("contabilidad", __name__, url_prefix="/contabilidad")


def _servicio():
    return ContabilidadService()


def _rango_desde_request():
    desde = parse_fecha(request.args.get("desde"), inicio_mes_actual())
    hasta = parse_fecha(request.args.get("hasta"), None) or date.today()
    if desde > hasta:
        desde, hasta = hasta, desde
    return desde, hasta


@contabilidad_bp.route("/libro-diario")
@role_required(Rol.ADMIN)
def libro_diario():
    desde, hasta = _rango_desde_request()
    inicio, fin = rango_fechas(desde, hasta)
    asientos = _servicio().libro_diario(inicio, fin)
    return render_template(
        "contabilidad/libro_diario.html",
        asientos=asientos,
        desde=desde,
        hasta=hasta,
        total_debe=round(sum(a.total_debe for a in asientos), 2),
        total_haber=round(sum(a.total_haber for a in asientos), 2),
    )


@contabilidad_bp.route("/gastos", methods=["GET", "POST"])
@role_required(Rol.ADMIN)
def gastos():
    servicio = _servicio()
    if request.method == "POST":
        try:
            servicio.registrar_gasto(
                categoria=request.form.get("categoria", ""),
                descripcion=request.form.get("descripcion", ""),
                monto=request.form.get("monto", type=float),
                estado=request.form.get("estado", EstadoPago.PAGADO),
                usuario_id=g.usuario.id,
            )
        except ErrorDeNegocio as error:
            db.session.rollback()
            flash(error.mensaje, "error")
        else:
            flash("Gasto registrado y asiento contable generado.", "exito")
        return redirect(url_for("contabilidad.gastos"))

    return render_template(
        "contabilidad/gastos.html",
        gastos=servicio.gastos.recientes(100),
        categorias=CATEGORIAS_GASTO,
    )


@contabilidad_bp.route("/gastos/<int:gasto_id>/pagar", methods=["POST"])
@role_required(Rol.ADMIN)
def pagar_gasto(gasto_id):
    try:
        _servicio().pagar_gasto(gasto_id, usuario_id=g.usuario.id)
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        flash("Gasto marcado como pagado.", "exito")
    return redirect(request.referrer or url_for("contabilidad.gastos"))


@contabilidad_bp.route("/compras/<int:movimiento_id>/pagar", methods=["POST"])
@role_required(Rol.ADMIN)
def pagar_compra(movimiento_id):
    try:
        _servicio().pagar_entrada_inventario(movimiento_id, usuario_id=g.usuario.id)
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        flash("Compra de inventario marcada como pagada.", "exito")
    return redirect(url_for("contabilidad.flujo_caja"))


@contabilidad_bp.route("/estado-resultados")
@role_required(Rol.ADMIN)
def estado_resultados():
    desde, hasta = _rango_desde_request()
    inicio, fin = rango_fechas(desde, hasta)
    resultado = _servicio().estado_resultados(inicio, fin)
    return render_template(
        "contabilidad/estado_resultados.html", r=resultado, desde=desde, hasta=hasta
    )


@contabilidad_bp.route("/flujo-caja")
@role_required(Rol.ADMIN)
def flujo_caja():
    return render_template("contabilidad/flujo_caja.html", flujo=_servicio().flujo_caja())
