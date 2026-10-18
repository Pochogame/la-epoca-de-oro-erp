from datetime import datetime

from app.constants import (
    CUENTA_COSTO_VENTAS,
    CUENTA_INVENTARIO,
    CUENTA_MERMAS,
    CUENTA_VENTAS,
    GUISADOS,
    GUISADO_A_INSUMO,
    PORCION_GUISADO_KG,
    EstadoComanda,
    EstadoMesa,
    MetodoPago,
    TipoOrden,
    Turno,
)
from app.extensions import db
from app.models.ventas import Comanda, Mesa, Venta, VentaDetalle
from app.repositories.inventario_repository import InsumoRepositorio
from app.repositories.menu_repository import ProductoRepositorio
from app.repositories.venta_repository import (
    ComandaRepositorio,
    MesaRepositorio,
    VentaRepositorio,
)
from app.services.contabilidad_service import ContabilidadService
from app.services.excepciones import DatosInvalidosError
from app.services.inventario_service import InventarioService


class VentaService:
    def __init__(
        self,
        ventas=None,
        comandas=None,
        productos=None,
        insumos=None,
        inventario=None,
        contabilidad=None,
        mesas=None,
    ):
        self.ventas = ventas or VentaRepositorio()
        self.comandas = comandas or ComandaRepositorio()
        self.productos = productos or ProductoRepositorio()
        self.insumos = insumos or InsumoRepositorio()
        self.inventario = inventario or InventarioService()
        self.contabilidad = contabilidad or ContabilidadService()
        self.mesas = mesas or MesaRepositorio()

    def _expandir_items(self, items, turno):
        lineas = []
        requerimientos = {}

        for item in items:
            producto = self.productos.obtener(int(item.get("producto_id") or 0))
            if producto is None or not producto.activo:
                raise DatosInvalidosError(
                    "Uno de los productos del pedido no existe o está inactivo."
                )
            if not producto.aplica_turno(turno):
                raise DatosInvalidosError(
                    f"El producto '{producto.nombre}' no pertenece al turno "
                    f"{Turno.ETIQUETAS[turno]}."
                )

            cantidad = int(item.get("cantidad") or 0)
            if cantidad < 1 or cantidad > 50:
                raise DatosInvalidosError(
                    f"La cantidad de '{producto.nombre}' debe estar entre 1 y 50."
                )

            guisado = (item.get("guisado") or "").strip()
            if producto.requiere_guisado:
                if guisado not in GUISADOS:
                    raise DatosInvalidosError(
                        f"Selecciona un guisado válido para '{producto.nombre}'."
                    )
            else:
                guisado = ""

            almacen_id = producto.almacen_consumo_id
            if almacen_id is None:
                raise DatosInvalidosError(
                    f"El producto '{producto.nombre}' no tiene almacén de consumo configurado."
                )

            costo_linea = 0.0
            for ingrediente in producto.receta:
                clave = (ingrediente.insumo_id, almacen_id)
                requerimientos[clave] = (
                    requerimientos.get(clave, 0.0) + ingrediente.cantidad * cantidad
                )
                costo_linea += (
                    ingrediente.cantidad * ingrediente.insumo.costo_unitario * cantidad
                )

            if guisado:
                insumo_guisado = self.insumos.por_codigo(GUISADO_A_INSUMO[guisado])
                if insumo_guisado is None:
                    raise DatosInvalidosError(
                        f"El insumo del guisado '{guisado}' no está configurado en el almacén."
                    )
                clave = (insumo_guisado.id, almacen_id)
                requerimientos[clave] = (
                    requerimientos.get(clave, 0.0) + PORCION_GUISADO_KG * cantidad
                )
                costo_linea += PORCION_GUISADO_KG * insumo_guisado.costo_unitario * cantidad

            subtotal = round(producto.precio * cantidad, 2)
            lineas.append(
                {
                    "producto": producto,
                    "cantidad": cantidad,
                    "guisado": guisado,
                    "precio_unitario": producto.precio,
                    "subtotal": subtotal,
                    "costo_linea": round(costo_linea, 2),
                }
            )

        return lineas, requerimientos

    def registrar_venta(
        self,
        mesero_id,
        turno,
        tipo_orden,
        metodo_pago,
        items,
        usuario_id=None,
        mesa_id=None,
    ):
        if turno not in Turno.TODOS:
            raise DatosInvalidosError("El turno seleccionado no es válido.")
        if tipo_orden not in (TipoOrden.AQUI, TipoOrden.LLEVAR):
            raise DatosInvalidosError("La modalidad de consumo no es válida.")
        if metodo_pago not in MetodoPago.TODOS:
            raise DatosInvalidosError("El método de pago no es válido.")
        if not items:
            raise DatosInvalidosError("El pedido no tiene productos. Agrega al menos uno.")

        mesa = None
        if tipo_orden == TipoOrden.AQUI and mesa_id:
            mesa = self.mesas.obtener(int(mesa_id))
            if mesa is None:
                raise DatosInvalidosError("La mesa seleccionada no existe.")
            if mesa.estado == EstadoMesa.RESERVADA:
                raise DatosInvalidosError(
                    f"La mesa {mesa.numero} está reservada. Elige otra mesa."
                )

        lineas, requerimientos = self._expandir_items(items, turno)
        self.inventario.verificar_disponibilidad(requerimientos)

        total = round(sum(linea["subtotal"] for linea in lineas), 2)
        costo_total = round(sum(linea["costo_linea"] for linea in lineas), 2)

        venta = Venta(
            folio=self.ventas.siguiente_folio(),
            turno=turno,
            tipo_orden=tipo_orden,
            metodo_pago=metodo_pago,
            total=total,
            costo_insumos=costo_total,
            mesero_id=mesero_id,
            mesa_id=mesa.id if mesa else None,
        )
        for linea in lineas:
            venta.detalles.append(
                VentaDetalle(
                    producto_id=linea["producto"].id,
                    producto_nombre=linea["producto"].nombre,
                    guisado=linea["guisado"],
                    cantidad=linea["cantidad"],
                    precio_unitario=linea["precio_unitario"],
                    subtotal=linea["subtotal"],
                    costo_linea=linea["costo_linea"],
                )
            )
        self.ventas.agregar(venta)
        db.session.flush()

        comanda = Comanda(
            folio=self.comandas.siguiente_folio(),
            venta_id=venta.id,
            turno=turno,
            tipo_orden=tipo_orden,
            estado=EstadoComanda.EN_PREPARACION,
        )
        self.comandas.agregar(comanda)

        if mesa is not None:
            mesa.estado = EstadoMesa.OCUPADA

        self.inventario.descontar_requerimientos(
            requerimientos, referencia=venta.folio, usuario_id=usuario_id
        )

        cuenta_cobro = MetodoPago.CUENTA_CONTABLE[metodo_pago]
        self.contabilidad.registrar_asiento(
            f"Venta {venta.folio} - {Turno.ETIQUETAS[turno]} - {TipoOrden.ETIQUETAS[tipo_orden]}",
            [(cuenta_cobro, total, 0.0), (CUENTA_VENTAS, 0.0, total)],
            origen="VENTA",
            referencia=venta.folio,
        )
        if costo_total > 0:
            self.contabilidad.registrar_asiento(
                f"Costo de venta (BOM) {venta.folio}",
                [(CUENTA_COSTO_VENTAS, costo_total, 0.0), (CUENTA_INVENTARIO, 0.0, costo_total)],
                origen="VENTA",
                referencia=venta.folio,
            )

        db.session.commit()
        return venta

    def comanda_de(self, comanda_id):
        return self.comandas.obtener(comanda_id)

    def marcar_comanda_lista(self, comanda_id):
        comanda = self.comandas.obtener(comanda_id)
        if comanda is None:
            raise DatosInvalidosError("La comanda indicada no existe.")
        if comanda.estado != EstadoComanda.EN_PREPARACION:
            raise DatosInvalidosError("Solo las comandas en preparación pueden marcarse como listas.")
        comanda.estado = EstadoComanda.LISTA
        comanda.lista_en = datetime.now()
        db.session.commit()
        return comanda

    def marcar_comanda_entregada(self, comanda_id):
        comanda = self.comandas.obtener(comanda_id)
        if comanda is None:
            raise DatosInvalidosError("La comanda indicada no existe.")
        if comanda.estado == EstadoComanda.ENTREGADA:
            raise DatosInvalidosError("La comanda ya fue entregada.")
        if comanda.estado == EstadoComanda.MERMA:
            raise DatosInvalidosError("La comanda fue registrada como merma.")
        comanda.estado = EstadoComanda.ENTREGADA
        comanda.entregada_en = datetime.now()
        db.session.commit()
        return comanda

    def marcar_comanda_merma(self, comanda_id, motivo, cancelar_venta=False, usuario_id=None):
        comanda = self.comandas.obtener(comanda_id)
        if comanda is None:
            raise DatosInvalidosError("La comanda indicada no existe.")
        if comanda.estado == EstadoComanda.MERMA:
            raise DatosInvalidosError("La comanda ya está registrada como merma.")

        venta = comanda.venta
        comanda.estado = EstadoComanda.MERMA
        comanda.merma_en = datetime.now()
        comanda.motivo_merma = (motivo or "Cliente no pasó por su platillo").strip()

        costo = round(venta.costo_insumos, 2)
        if costo > 0:
            self.contabilidad.registrar_asiento(
                f"Merma de platillo (comanda {comanda.folio}): {comanda.motivo_merma}",
                [(CUENTA_MERMAS, costo, 0.0), (CUENTA_COSTO_VENTAS, 0.0, costo)],
                origen="MERMA",
                referencia=venta.folio,
            )

        if cancelar_venta:
            venta.cancelada = True
            venta.cancelada_en = datetime.now()
            venta.motivo_cancelacion = comanda.motivo_merma
            cuenta_cobro = MetodoPago.CUENTA_CONTABLE[venta.metodo_pago]
            self.contabilidad.registrar_asiento(
                f"Cancelación de venta {venta.folio}: {comanda.motivo_merma}",
                [(CUENTA_VENTAS, venta.total, 0.0), (cuenta_cobro, 0.0, venta.total)],
                origen="CANCELACION",
                referencia=venta.folio,
            )

        self._liberar_mesa_si_aplica(venta)
        db.session.commit()
        return comanda

    def cerrar_comanda(self, comanda_id, usuario_id=None):
        comanda = self.comandas.obtener(comanda_id)
        if comanda is None:
            raise DatosInvalidosError("La comanda indicada no existe.")
        if comanda.estado in (EstadoComanda.EN_PREPARACION, EstadoComanda.LISTA):
            raise DatosInvalidosError(
                "La comanda todavía no se entrega ni se registra como merma."
            )
        if comanda.cerrada_en is not None:
            raise DatosInvalidosError("La comanda ya fue cerrada.")
        comanda.cerrada_en = datetime.now()
        comanda.cerrada_por_id = usuario_id
        self._liberar_mesa_si_aplica(comanda.venta)
        db.session.commit()
        return comanda

    def _liberar_mesa_si_aplica(self, venta):
        if venta.mesa is None:
            return
        if not venta.mesa.comandas_activas:
            venta.mesa.estado = EstadoMesa.LIMPIEZA

    def cambiar_estado_mesa(self, mesa_id, estado):
        mesa = self.mesas.obtener(mesa_id)
        if mesa is None:
            raise DatosInvalidosError("La mesa indicada no existe.")
        if estado not in EstadoMesa.TODOS:
            raise DatosInvalidosError("El estado de la mesa no es válido.")
        if estado == EstadoMesa.LIBRE and mesa.comandas_activas:
            raise DatosInvalidosError(
                "La mesa tiene comandas activas; no puede marcarse como libre todavía."
            )
        mesa.estado = estado
        db.session.commit()
        return mesa

    def detalle_comanda(self, comanda_id):
        comanda = self.comandas.obtener(comanda_id)
        if comanda is None:
            return None

        requerimientos = {}
        lineas = []
        for detalle in comanda.venta.detalles:
            producto = detalle.producto
            almacen_id = producto.almacen_consumo_id
            ingredientes = []
            for ingrediente in producto.receta:
                cantidad = ingrediente.cantidad * detalle.cantidad
                clave = (ingrediente.insumo_id, almacen_id)
                requerimientos[clave] = requerimientos.get(clave, 0.0) + cantidad
                ingredientes.append(
                    {
                        "insumo": ingrediente.insumo,
                        "cantidad": round(cantidad, 4),
                        "almacen": producto.almacen_consumo,
                    }
                )
            if detalle.guisado:
                insumo_guisado = self.insumos.por_codigo(GUISADO_A_INSUMO[detalle.guisado])
                if insumo_guisado is not None:
                    cantidad = PORCION_GUISADO_KG * detalle.cantidad
                    clave = (insumo_guisado.id, almacen_id)
                    requerimientos[clave] = requerimientos.get(clave, 0.0) + cantidad
                    ingredientes.append(
                        {
                            "insumo": insumo_guisado,
                            "cantidad": round(cantidad, 4),
                            "almacen": producto.almacen_consumo,
                        }
                    )
            lineas.append({"detalle": detalle, "ingredientes": ingredientes})

        consumos = []
        for (insumo_id, almacen_id), cantidad in sorted(requerimientos.items()):
            insumo = self.insumos.obtener(insumo_id)
            stock = self.inventario.stock_de(insumo_id, almacen_id)
            if stock <= 0:
                estado = "AGOTADO"
            elif insumo.bajo_minimo:
                estado = "BAJO"
            else:
                estado = "OK"
            consumos.append(
                {
                    "insumo": insumo,
                    "cantidad": round(cantidad, 4),
                    "stock": stock,
                    "estado": estado,
                }
            )

        agotados = [consumo for consumo in consumos if consumo["estado"] == "AGOTADO"]
        return {
            "comanda": comanda,
            "lineas": lineas,
            "consumos": consumos,
            "agotados": agotados,
        }

    def comandas_activas(self):
        return self.comandas.activas()

    def comandas_pendientes_de(self, mesero_id):
        return self.comandas.pendientes_de_mesero(mesero_id)

    def mesas_por_zona(self):
        return self.mesas.por_zona()

    def historial_comandas(self, limite=50):
        return self.comandas.historial(limite)

    def venta_de(self, venta_id):
        return self.ventas.obtener(venta_id)

    def pedidos_del_mesero(self, mesero_id, limite=30):
        return self.ventas.del_mesero(mesero_id, limite)

    def ventas_recientes(self, limite=50):
        return self.ventas.recientes(limite)
