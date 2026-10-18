from datetime import date

from flask import Blueprint, g, redirect, render_template, url_for

from app.security import login_required
from app.services.contabilidad_service import ContabilidadService
from app.services.inventario_service import InventarioService
from app.services.venta_service import VentaService
from app.utilidades import inicio_mes_actual, rango_dia, rango_fechas

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    if g.usuario.es_mesero:
        return redirect(url_for("pos.index"))
    if g.usuario.es_chef:
        return redirect(url_for("cocina.index"))

    ventas = VentaService()
    inventario = InventarioService()
    contabilidad = ContabilidadService()

    inicio_dia, fin_dia = rango_dia(date.today())
    inicio_mes, fin_mes = rango_fechas(inicio_mes_actual(), date.today())

    ventas_hoy = ventas.ventas.en_rango(inicio_dia, fin_dia)

    return render_template(
        "dashboard/index.html",
        total_hoy=round(sum(venta.total for venta in ventas_hoy), 2),
        tickets_hoy=len(ventas_hoy),
        comandas_activas=ventas.comandas_activas(),
        alertas=inventario.alertas(),
        flujo=contabilidad.flujo_caja(),
        resultado_mes=contabilidad.estado_resultados(inicio_mes, fin_mes),
        ultimas_ventas=ventas.ventas_recientes(8),
    )
