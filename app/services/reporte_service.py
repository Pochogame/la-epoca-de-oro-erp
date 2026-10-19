from datetime import date, datetime, time, timedelta

from app.constants import Turno
from app.extensions import db
from app.models.ventas import Venta, VentaDetalle
from app.utilidades import rango_fechas


class ReporteService:
    def resumen(self, desde, hasta):
        ventas = (
            Venta.query.filter(
                Venta.fecha >= desde,
                Venta.fecha <= hasta,
                Venta.cancelada.is_(False),
                Venta.cobrada_en.isnot(None),
            )
            .order_by(Venta.fecha)
            .all()
        )

        por_dia = {}
        dia = desde.date()
        while dia <= hasta.date():
            por_dia[dia] = 0.0
            dia += timedelta(days=1)
        for venta in ventas:
            por_dia[venta.fecha.date()] = round(
                por_dia.get(venta.fecha.date(), 0.0) + venta.total, 2
            )

        por_hora = {hora: {"total": 0.0, "tickets": 0} for hora in range(7, 23)}
        for venta in ventas:
            hora = venta.fecha.hour
            if hora in por_hora:
                por_hora[hora]["total"] = round(por_hora[hora]["total"] + venta.total, 2)
                por_hora[hora]["tickets"] += 1

        top = (
            db.session.query(
                VentaDetalle.producto_nombre,
                db.func.sum(VentaDetalle.cantidad).label("piezas"),
                db.func.sum(VentaDetalle.subtotal).label("ingresos"),
            )
            .join(Venta)
            .filter(
                Venta.fecha >= desde,
                Venta.fecha <= hasta,
                Venta.cancelada.is_(False),
                Venta.cobrada_en.isnot(None),
                VentaDetalle.cancelado.is_(False),
            )
            .group_by(VentaDetalle.producto_nombre)
            .order_by(db.func.sum(VentaDetalle.cantidad).desc())
            .limit(10)
            .all()
        )

        por_turno = {turno: 0.0 for turno in Turno.TODOS}
        for venta in ventas:
            por_turno[venta.turno] = round(por_turno.get(venta.turno, 0.0) + venta.total, 2)

        por_mesa = {}
        for venta in ventas:
            if venta.mesa is None:
                continue
            datos = por_mesa.setdefault(
                venta.mesa.numero, {"tickets": 0, "total": 0.0}
            )
            datos["tickets"] += 1
            datos["total"] = round(datos["total"] + venta.total, 2)
        mesas = [
            {
                "mesa": numero,
                "tickets": datos["tickets"],
                "total": datos["total"],
                "promedio": round(datos["total"] / datos["tickets"], 2),
            }
            for numero, datos in sorted(por_mesa.items())
        ]
        mesas.sort(key=lambda fila: fila["total"], reverse=True)

        total = round(sum(venta.total for venta in ventas), 2)
        dias_con_ventas = len({venta.fecha.date() for venta in ventas}) or 0
        dias_rango = (hasta.date() - desde.date()).days + 1
        promedio_diario = round(total / dias_rango, 2) if dias_rango > 0 else 0.0
        proyeccion_semanal = round(promedio_diario * 7, 2)
        dias_mes = 30
        proyeccion_mensual = round(promedio_diario * dias_mes, 2)

        return {
            "desde": desde,
            "hasta": hasta,
            "ventas": ventas,
            "total": total,
            "tickets": len(ventas),
            "ticket_promedio": round(total / len(ventas), 2) if ventas else 0.0,
            "por_dia": por_dia,
            "por_hora": por_hora,
            "top_productos": [
                {"nombre": fila[0], "piezas": int(fila[1] or 0), "ingresos": round(fila[2] or 0, 2)}
                for fila in top
            ],
            "por_turno": por_turno,
            "mesas": mesas,
            "promedio_diario": promedio_diario,
            "proyeccion_semanal": proyeccion_semanal,
            "proyeccion_mensual": proyeccion_mensual,
            "dias_con_ventas": dias_con_ventas,
        }

    def rangos_disponibles(self):
        hoy = date.today()
        return {
            "semana": (datetime.combine(hoy - timedelta(days=6), time.min), datetime.combine(hoy, time.max)),
            "mes": rango_fechas(hoy.replace(day=1), hoy),
            "anio": rango_fechas(hoy.replace(month=1, day=1), hoy),
        }
