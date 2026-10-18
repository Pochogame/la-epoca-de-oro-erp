from app.constants import (
    CUENTA_CAJA,
    CUENTA_CXP,
    CUENTA_INVENTARIO,
    CUENTA_MERMAS,
    MOTIVOS_MERMA,
    EstadoPago,
    TipoMovimiento,
)
from app.extensions import db
from app.models.inventario import Insumo, Merma, MovimientoInventario
from app.repositories.inventario_repository import (
    AlmacenRepositorio,
    InsumoRepositorio,
    MermaRepositorio,
    MovimientoRepositorio,
)
from app.services.contabilidad_service import ContabilidadService
from app.services.excepciones import DatosInvalidosError, StockInsuficienteError


class InventarioService:
    def __init__(
        self, insumos=None, almacenes=None, mermas=None, movimientos_repo=None, contabilidad=None
    ):
        self.insumos = insumos or InsumoRepositorio()
        self.almacenes = almacenes or AlmacenRepositorio()
        self.mermas = mermas or MermaRepositorio()
        self.movimientos_repo = movimientos_repo or MovimientoRepositorio()
        self.contabilidad = contabilidad or ContabilidadService()

    def almacen_por_codigo(self, codigo):
        almacen = self.almacenes.por_codigo(codigo)
        if almacen is None:
            raise DatosInvalidosError(f"El almacén {codigo} no existe.")
        return almacen

    def stock_de(self, insumo_id, almacen_id):
        stock = self.insumos.stock(insumo_id, almacen_id)
        return round(stock.cantidad, 4) if stock else 0.0

    def _mover_stock(self, insumo, almacen_origen_id, almacen_destino_id, cantidad):
        if almacen_origen_id:
            stock_origen = self.insumos.asegurar_stock(insumo.id, almacen_origen_id)
            if stock_origen.cantidad + 1e-9 < cantidad:
                almacen = self.almacenes.obtener(almacen_origen_id)
                raise StockInsuficienteError(
                    f"Stock insuficiente de {insumo.nombre} en {almacen.nombre}: "
                    f"disponible {stock_origen.cantidad:.3f} {insumo.unidad}, "
                    f"requerido {cantidad:.3f} {insumo.unidad}."
                )
            stock_origen.cantidad = round(stock_origen.cantidad - cantidad, 4)
        if almacen_destino_id:
            stock_destino = self.insumos.asegurar_stock(insumo.id, almacen_destino_id)
            stock_destino.cantidad = round(stock_destino.cantidad + cantidad, 4)

    def registrar_entrada(
        self,
        insumo_id,
        cantidad,
        costo_unitario,
        almacen_destino_id,
        usuario_id,
        estado_pago=EstadoPago.PAGADO,
        referencia="",
    ):
        insumo = self.insumos.obtener(insumo_id)
        if insumo is None:
            raise DatosInvalidosError("El insumo indicado no existe.")
        if cantidad is None or cantidad <= 0:
            raise DatosInvalidosError("La cantidad recibida debe ser mayor a cero.")
        if costo_unitario is None or costo_unitario < 0:
            raise DatosInvalidosError("El costo unitario no puede ser negativo.")
        almacen = self.almacenes.obtener(almacen_destino_id)
        if almacen is None:
            raise DatosInvalidosError("El almacén destino no existe.")
        if estado_pago not in (EstadoPago.PAGADO, EstadoPago.PENDIENTE):
            raise DatosInvalidosError("El estado de pago no es válido.")

        costo_unitario = round(float(costo_unitario), 2)
        cantidad = round(float(cantidad), 4)
        total = round(cantidad * costo_unitario, 2)

        movimiento = MovimientoInventario(
            tipo=TipoMovimiento.ENTRADA,
            insumo_id=insumo.id,
            almacen_destino_id=almacen.id,
            cantidad=cantidad,
            costo_unitario=costo_unitario,
            costo_total=total,
            estado_pago=estado_pago,
            referencia=referencia or "Compra de insumos",
            usuario_id=usuario_id,
        )
        self.insumos.agregar(movimiento)
        self._mover_stock(insumo, None, almacen.id, cantidad)

        if costo_unitario > 0:
            insumo.costo_unitario = costo_unitario

        db.session.flush()
        if total > 0:
            cuenta_credito = CUENTA_CAJA if estado_pago == EstadoPago.PAGADO else CUENTA_CXP
            self.contabilidad.registrar_asiento(
                f"Compra de {insumo.nombre}: {cantidad:g} {insumo.unidad} a ${costo_unitario:,.2f}",
                [(CUENTA_INVENTARIO, total, 0.0), (cuenta_credito, 0.0, total)],
                origen="COMPRA",
                referencia=f"MOV-{movimiento.id}",
            )
        db.session.commit()
        return movimiento

    def transferir(self, insumo_id, almacen_origen_id, almacen_destino_id, cantidad, usuario_id):
        insumo = self.insumos.obtener(insumo_id)
        if insumo is None:
            raise DatosInvalidosError("El insumo indicado no existe.")
        if almacen_origen_id == almacen_destino_id:
            raise DatosInvalidosError("El almacén de origen y destino deben ser diferentes.")
        if cantidad is None or cantidad <= 0:
            raise DatosInvalidosError("La cantidad a transferir debe ser mayor a cero.")

        cantidad = round(float(cantidad), 4)
        movimiento = MovimientoInventario(
            tipo=TipoMovimiento.TRANSFERENCIA,
            insumo_id=insumo.id,
            almacen_origen_id=almacen_origen_id,
            almacen_destino_id=almacen_destino_id,
            cantidad=cantidad,
            costo_unitario=insumo.costo_unitario,
            costo_total=round(cantidad * insumo.costo_unitario, 2),
            referencia="Transferencia interna",
            estado_pago=EstadoPago.NO_APLICA,
            usuario_id=usuario_id,
        )
        self.insumos.agregar(movimiento)
        self._mover_stock(insumo, almacen_origen_id, almacen_destino_id, cantidad)
        db.session.commit()
        return movimiento

    def registrar_merma(self, insumo_id, almacen_id, cantidad, motivo, comentario, usuario_id):
        insumo = self.insumos.obtener(insumo_id)
        if insumo is None:
            raise DatosInvalidosError("El insumo indicado no existe.")
        if motivo not in MOTIVOS_MERMA:
            raise DatosInvalidosError("El motivo de la merma no es válido.")
        if cantidad is None or cantidad <= 0:
            raise DatosInvalidosError("La cantidad de la merma debe ser mayor a cero.")

        cantidad = round(float(cantidad), 4)
        costo_estimado = round(cantidad * insumo.costo_unitario, 2)
        merma = Merma(
            insumo_id=insumo.id,
            almacen_id=almacen_id,
            cantidad=cantidad,
            motivo=motivo,
            comentario=(comentario or "").strip(),
            costo_estimado=costo_estimado,
            usuario_id=usuario_id,
        )
        movimiento = MovimientoInventario(
            tipo=TipoMovimiento.MERMA,
            insumo_id=insumo.id,
            almacen_origen_id=almacen_id,
            cantidad=cantidad,
            costo_unitario=insumo.costo_unitario,
            costo_total=costo_estimado,
            motivo=motivo,
            referencia="Merma registrada",
            estado_pago=EstadoPago.NO_APLICA,
            usuario_id=usuario_id,
        )
        self.insumos.agregar(movimiento)
        self.mermas.agregar(merma)
        self._mover_stock(insumo, almacen_id, None, cantidad)

        if costo_estimado > 0:
            self.contabilidad.registrar_asiento(
                f"Merma de {insumo.nombre} ({motivo})",
                [(CUENTA_MERMAS, costo_estimado, 0.0), (CUENTA_INVENTARIO, 0.0, costo_estimado)],
                origen="MERMA",
                referencia=f"MERMA-{merma.id or ''}",
            )
        db.session.commit()
        return merma

    def verificar_disponibilidad(self, requerimientos):
        faltantes = []
        for (insumo_id, almacen_id), cantidad in requerimientos.items():
            disponible = self.stock_de(insumo_id, almacen_id)
            if disponible + 1e-9 < cantidad:
                insumo = self.insumos.obtener(insumo_id)
                almacen = self.almacenes.obtener(almacen_id)
                faltantes.append(
                    f"{insumo.nombre} en {almacen.nombre}: disponible {disponible:.3f} "
                    f"{insumo.unidad}, requerido {cantidad:.3f} {insumo.unidad}"
                )
        if faltantes:
            detalle = "; ".join(faltantes)
            raise StockInsuficienteError(
                f"No hay stock suficiente para completar la venta. Faltantes: {detalle}. "
                "Realiza una entrada o transferencia de insumos."
            )

    def descontar_requerimientos(self, requerimientos, referencia, usuario_id=None):
        self.verificar_disponibilidad(requerimientos)
        for (insumo_id, almacen_id), cantidad in requerimientos.items():
            insumo = self.insumos.obtener(insumo_id)
            movimiento = MovimientoInventario(
                tipo=TipoMovimiento.SALIDA_VENTA,
                insumo_id=insumo_id,
                almacen_origen_id=almacen_id,
                cantidad=round(cantidad, 4),
                costo_unitario=insumo.costo_unitario,
                costo_total=round(cantidad * insumo.costo_unitario, 2),
                referencia=referencia,
                estado_pago=EstadoPago.NO_APLICA,
                usuario_id=usuario_id,
            )
            self.insumos.agregar(movimiento)
            self._mover_stock(insumo, almacen_id, None, round(cantidad, 4))

    def crear_insumo(self, codigo, nombre, unidad, costo_unitario, stock_minimo):
        codigo = (codigo or "").strip().upper()
        nombre = (nombre or "").strip()
        if not codigo or not nombre:
            raise DatosInvalidosError("El código y el nombre del insumo son obligatorios.")
        if self.insumos.por_codigo(codigo):
            raise DatosInvalidosError(f"Ya existe un insumo con el código {codigo}.")
        if unidad not in ("kg", "L", "pza"):
            raise DatosInvalidosError("La unidad debe ser kg, L o pza.")
        insumo = Insumo(
            codigo=codigo,
            nombre=nombre,
            unidad=unidad,
            costo_unitario=max(float(costo_unitario or 0), 0),
            stock_minimo=max(float(stock_minimo or 0), 0),
        )
        self.insumos.agregar(insumo)
        db.session.commit()
        return insumo

    def alertas(self):
        return self.insumos.alertas()

    def movimientos(self, limite=100):
        return self.movimientos_repo.movimientos(limite)

    def panel_almacenes(self):
        panel = []
        for almacen in self.almacenes.todos_ordenados():
            panel.append(
                {"almacen": almacen, "stocks": self.insumos.stocks_por_almacen(almacen.id)}
            )
        return panel
