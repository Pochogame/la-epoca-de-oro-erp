from datetime import datetime

from app.constants import (
    CATEGORIAS_GASTO,
    CUENTA_BANCOS,
    CUENTA_CAJA,
    CUENTA_CXP,
    CUENTA_INVENTARIO,
    EstadoPago,
    Turno,
)
from app.extensions import db
from app.models.contabilidad import Asiento, AsientoLinea, GastoOperativo
from app.repositories.contabilidad_repository import (
    AsientoRepositorio,
    CuentaContableRepositorio,
    GastoRepositorio,
)
from app.repositories.inventario_repository import MermaRepositorio, MovimientoRepositorio
from app.repositories.venta_repository import VentaRepositorio
from app.services.excepciones import DatosInvalidosError, OperacionDuplicadaError


class ContabilidadService:
    def __init__(
        self,
        asientos=None,
        cuentas=None,
        gastos=None,
        ventas=None,
        mermas=None,
        movimientos=None,
    ):
        self.asientos = asientos or AsientoRepositorio()
        self.cuentas = cuentas or CuentaContableRepositorio()
        self.gastos = gastos or GastoRepositorio()
        self.ventas = ventas or VentaRepositorio()
        self.mermas = mermas or MermaRepositorio()
        self.movimientos = movimientos or MovimientoRepositorio()

    def registrar_asiento(self, concepto, lineas, origen="AUTOMATICO", referencia=""):
        total_debe = round(sum(linea[1] for linea in lineas), 2)
        total_haber = round(sum(linea[2] for linea in lineas), 2)
        if abs(total_debe - total_haber) > 0.01:
            raise DatosInvalidosError(
                f"Asiento descuadrado: debe {total_debe:.2f} vs haber {total_haber:.2f}."
            )
        if total_debe <= 0:
            raise DatosInvalidosError("El asiento no puede ser por importe cero.")

        asiento = Asiento(
            folio=self.asientos.siguiente_folio(),
            concepto=concepto,
            origen=origen,
            referencia=referencia,
        )
        for codigo, debe, haber in lineas:
            cuenta = self.cuentas.por_codigo(codigo)
            if cuenta is None:
                raise DatosInvalidosError(f"La cuenta contable {codigo} no existe en el catálogo.")
            asiento.lineas.append(
                AsientoLinea(cuenta_id=cuenta.id, debe=round(debe, 2), haber=round(haber, 2))
            )
        self.asientos.agregar(asiento)
        return asiento

    def registrar_gasto(
        self,
        categoria,
        descripcion,
        monto,
        estado=EstadoPago.PAGADO,
        usuario_id=None,
        autocommit=True,
    ):
        if categoria not in CATEGORIAS_GASTO:
            raise DatosInvalidosError(f"La categoría de gasto '{categoria}' no es válida.")
        if monto is None or monto <= 0:
            raise DatosInvalidosError("El monto del gasto debe ser mayor a cero.")
        codigo_gasto, nombre_categoria = CATEGORIAS_GASTO[categoria]

        gasto = GastoOperativo(
            categoria=categoria,
            descripcion=descripcion.strip() or nombre_categoria,
            monto=round(float(monto), 2),
            estado=estado,
            usuario_id=usuario_id,
        )
        if estado == EstadoPago.PAGADO:
            gasto.fecha_pago = datetime.now()
        self.gastos.agregar(gasto)
        db.session.flush()

        cuenta_credito = CUENTA_CAJA if estado == EstadoPago.PAGADO else CUENTA_CXP
        self.registrar_asiento(
            f"Gasto {nombre_categoria}: {gasto.descripcion}",
            [(codigo_gasto, gasto.monto, 0.0), (cuenta_credito, 0.0, gasto.monto)],
            origen="GASTO",
            referencia=f"GASTO-{gasto.id}",
        )
        if autocommit:
            db.session.commit()
        return gasto

    def pagar_gasto(self, gasto_id, usuario_id=None):
        gasto = self.gastos.obtener(gasto_id)
        if gasto is None:
            raise DatosInvalidosError("El gasto indicado no existe.")
        if gasto.estado != EstadoPago.PENDIENTE:
            raise OperacionDuplicadaError("El gasto ya se encuentra pagado.")
        gasto.estado = EstadoPago.PAGADO
        gasto.fecha_pago = datetime.now()
        self.registrar_asiento(
            f"Pago de gasto pendiente: {gasto.descripcion}",
            [(CUENTA_CXP, gasto.monto, 0.0), (CUENTA_CAJA, 0.0, gasto.monto)],
            origen="PAGO",
            referencia=f"GASTO-{gasto.id}",
        )
        db.session.commit()
        return gasto

    def pagar_entrada_inventario(self, movimiento_id, usuario_id=None):
        movimiento = self.movimientos.obtener(movimiento_id)
        if movimiento is None:
            raise DatosInvalidosError("El movimiento de compra indicado no existe.")
        if movimiento.tipo != "ENTRADA":
            raise DatosInvalidosError("Solo se pueden pagar movimientos de compra.")
        if movimiento.estado_pago != EstadoPago.PENDIENTE:
            raise OperacionDuplicadaError("La compra ya se encuentra pagada.")
        movimiento.estado_pago = EstadoPago.PAGADO
        self.registrar_asiento(
            f"Pago de compra {movimiento.referencia or movimiento.id}: {movimiento.insumo.nombre}",
            [(CUENTA_CXP, movimiento.costo_total, 0.0), (CUENTA_CAJA, 0.0, movimiento.costo_total)],
            origen="PAGO",
            referencia=f"MOV-{movimiento.id}",
        )
        db.session.commit()
        return movimiento

    def libro_diario(self, desde, hasta):
        return self.asientos.en_rango(desde, hasta)

    def estado_resultados(self, desde, hasta):
        ventas = self.ventas.en_rango(desde, hasta)
        ventas_manana = round(sum(v.total for v in ventas if v.turno == Turno.MANANA), 2)
        ventas_tarde = round(sum(v.total for v in ventas if v.turno == Turno.TARDE), 2)
        ventas_total = round(ventas_manana + ventas_tarde, 2)
        costo_ventas = round(sum(v.costo_insumos for v in ventas), 2)
        utilidad_bruta = round(ventas_total - costo_ventas, 2)

        mermas = round(sum(m.costo_estimado for m in self.mermas.en_rango(desde, hasta)), 2)

        gastos = self.gastos.en_rango(desde, hasta)
        nomina = round(sum(g.monto for g in gastos if g.categoria == "NOMINA"), 2)
        acumulado = {}
        for gasto in gastos:
            if gasto.categoria == "NOMINA":
                continue
            acumulado[gasto.categoria] = acumulado.get(gasto.categoria, 0.0) + gasto.monto
        lineas_gastos = [
            {
                "categoria": categoria,
                "concepto": CATEGORIAS_GASTO[categoria][1],
                "monto": round(monto, 2),
            }
            for categoria, monto in sorted(acumulado.items(), key=lambda par: par[0])
        ]
        total_gastos_operativos = round(sum(item["monto"] for item in lineas_gastos), 2)

        utilidad_neta = round(
            utilidad_bruta - mermas - total_gastos_operativos - nomina, 2
        )
        margen_bruto = round(utilidad_bruta / ventas_total * 100, 1) if ventas_total else 0.0
        margen_neto = round(utilidad_neta / ventas_total * 100, 1) if ventas_total else 0.0
        ticket_promedio = round(ventas_total / len(ventas), 2) if ventas else 0.0

        return {
            "desde": desde,
            "hasta": hasta,
            "ventas_manana": ventas_manana,
            "ventas_tarde": ventas_tarde,
            "ventas_total": ventas_total,
            "num_ventas": len(ventas),
            "ticket_promedio": ticket_promedio,
            "costo_ventas": costo_ventas,
            "utilidad_bruta": utilidad_bruta,
            "mermas": mermas,
            "nomina": nomina,
            "lineas_gastos": lineas_gastos,
            "total_gastos_operativos": total_gastos_operativos,
            "utilidad_neta": utilidad_neta,
            "margen_bruto": margen_bruto,
            "margen_neto": margen_neto,
        }

    def flujo_caja(self):
        caja = self.asientos.saldo_cuenta(CUENTA_CAJA)
        bancos = self.asientos.saldo_cuenta(CUENTA_BANCOS)
        cxp = self.asientos.saldo_cuenta(CUENTA_CXP)
        inventario = self.asientos.saldo_cuenta(CUENTA_INVENTARIO)
        return {
            "caja": caja,
            "bancos": bancos,
            "efectivo_disponible": round(caja + bancos, 2),
            "cuentas_por_pagar": round(-cxp, 2) if cxp < 0 else cxp,
            "inventario": inventario,
            "gastos_pendientes": self.gastos.pendientes(),
            "compras_pendientes": self.movimientos.movimientos_entrada_pendientes(),
        }

    def cuentas_con_saldos(self):
        saldos = []
        for cuenta in self.cuentas.catalogo():
            saldos.append({"cuenta": cuenta, "saldo": self.asientos.saldo_cuenta(cuenta.codigo)})
        return saldos
