from datetime import date, datetime, time, timedelta

from flask import Blueprint, render_template, request

from app.constants import Rol
from app.security import role_required
from app.services.reporte_service import ReporteService
from app.utilidades import rango_fechas

reportes_bp = Blueprint("reportes", __name__, url_prefix="/reportes")


def _rango_solicitado():
    hoy = date.today()
    preset = request.args.get("rango", "mes")
    if preset == "semana":
        desde = datetime.combine(hoy - timedelta(days=6), time.min)
    elif preset == "anio":
        desde = datetime.combine(hoy.replace(month=1, day=1), time.min)
    else:
        preset = "mes"
        desde = datetime.combine(hoy.replace(day=1), time.min)
    return desde, datetime.combine(hoy, time.max), preset


@reportes_bp.route("/")
@role_required(Rol.ADMIN)
def index():
    desde, hasta, preset = _rango_solicitado()
    resumen = ReporteService().resumen(desde, hasta)
    return render_template("reportes/index.html", resumen=resumen, preset=preset)
