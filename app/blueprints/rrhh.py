from datetime import date

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app.constants import EstadoAsistencia, Rol
from app.extensions import db
from app.security import role_required
from app.services.excepciones import ErrorDeNegocio
from app.services.rrhh_service import RRHHService
from app.utilidades import (
    fin_semana_actual,
    inicio_mes_actual,
    inicio_semana_actual,
    parse_fecha,
)

rrhh_bp = Blueprint("rrhh", __name__, url_prefix="/rrhh")


def _servicio():
    return RRHHService()


@rrhh_bp.route("/asistencias", methods=["GET", "POST"])
@role_required(Rol.ADMIN)
def asistencias():
    servicio = _servicio()
    if request.method == "POST":
        accion = request.form.get("accion")
        if accion:
            try:
                asistencia = servicio.marcar_jornada(
                    usuario_id=request.form.get("usuario_id", type=int),
                    fecha=date.today(),
                    accion=accion,
                )
            except ErrorDeNegocio as error:
                db.session.rollback()
                flash(error.mensaje, "error")
            else:
                flash(
                    f"Marca registrada: {asistencia.usuario.nombre} · "
                    f"{asistencia.estado.lower()} a las "
                    f"{(asistencia.hora_salida or asistencia.hora_entrada).strftime('%H:%M')}.",
                    "exito",
                )
            return redirect(url_for("rrhh.asistencias"))

        hora_entrada = request.form.get("hora_entrada") or None
        hora_salida = request.form.get("hora_salida") or None
        try:
            servicio.registrar_asistencia(
                usuario_id=request.form.get("usuario_id", type=int),
                fecha=parse_fecha(request.form.get("fecha"), date.today()),
                hora_entrada=_parse_hora(hora_entrada),
                hora_salida=_parse_hora(hora_salida),
                estado=request.form.get("estado", EstadoAsistencia.PRESENTE),
            )
        except ErrorDeNegocio as error:
            db.session.rollback()
            flash(error.mensaje, "error")
        else:
            flash("Asistencia registrada.", "exito")
        return redirect(url_for("rrhh.asistencias"))

    usuario_id = request.args.get("usuario_id", type=int)
    hoy = date.today()
    asistencias = servicio.listar_asistencias(hoy.replace(day=1), hoy, usuario_id=usuario_id)
    return render_template(
        "rrhh/asistencias.html",
        empleados=servicio.usuarios.activos(),
        asistencias=asistencias,
        asistencias_hoy={a.usuario_id: a for a in servicio.listar_asistencias(hoy, hoy)},
        estados=EstadoAsistencia.ETIQUETAS,
        usuario_filtro=usuario_id,
        hoy=hoy,
    )


@rrhh_bp.route("/nomina")
@role_required(Rol.ADMIN)
def nomina():
    desde, hasta = _periodo_desde_request()
    servicio = _servicio()
    calculo = servicio.calcular_nomina(desde, hasta)
    return render_template(
        "rrhh/nomina.html",
        calculo=calculo,
        desde=desde,
        hasta=hasta,
        historial=servicio.historial_pagos(),
    )


@rrhh_bp.route("/nomina/pagar", methods=["POST"])
@role_required(Rol.ADMIN)
def pagar_nomina():
    desde = parse_fecha(request.form.get("desde"), inicio_semana_actual())
    hasta = parse_fecha(request.form.get("hasta"), fin_semana_actual())
    try:
        nomina = _servicio().registrar_pago(desde, hasta, usuario_id=g.usuario.id)
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        flash(
            f"Nómina pagada y registrada en contabilidad por ${nomina.total:,.2f} MXN.",
            "exito",
        )
        return redirect(url_for("rrhh.nomina", desde=desde.isoformat(), hasta=hasta.isoformat()))

    return redirect(
        url_for("rrhh.nomina", desde=desde.isoformat(), hasta=hasta.isoformat())
    )


def _periodo_desde_request():
    periodo = request.args.get("periodo", "semana")
    if periodo == "mes":
        return inicio_mes_actual(), date.today()
    if periodo == "manual":
        desde = parse_fecha(request.args.get("desde"), inicio_semana_actual())
        hasta = parse_fecha(request.args.get("hasta"), fin_semana_actual())
        if desde > hasta:
            desde, hasta = hasta, desde
        return desde, hasta
    return inicio_semana_actual(), fin_semana_actual()


def _parse_hora(texto):
    if not texto:
        return None
    from datetime import datetime

    try:
        return datetime.strptime(texto.strip(), "%H:%M").time()
    except ValueError:
        return None
