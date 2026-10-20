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
from app.models.crm import Cliente
from app.models.ventas import (
    CancelacionPlatillo,
    Comanda,
    CuentaMesa,
    Mesa,
    Venta,
    VentaDetalle,
)
from app.repositories.inventario_repository import InsumoRepositorio
from app.repositories.menu_repository import ProductoRepositorio
from app.repositories.usuario_repository import UsuarioRepositorio
from app.repositories.venta_repository import (
    CancelacionRepositorio,
    ComandaRepositorio,
    CuentaMesaRepositorio,
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
        cuentas=None,
        cancelaciones=None,
        usuarios=None,
    ):
        self.ventas = ventas or VentaRepositorio()
        self.comandas = comandas or ComandaRepositorio()
        self.productos = productos or ProductoRepositorio()
        self.insumos = insumos or InsumoRepositorio()
        self.inventario = inventario or InventarioService()
        self.contabilidad = contabilidad or ContabilidadService()
        self.mesas = mesas or MesaRepositorio()
        self.cuentas = cuentas or CuentaMesaRepositorio()
        self.cancelaciones = cancelaciones or CancelacionRepositorio()
        self.usuarios = usuarios or UsuarioRepositorio()

    def _resolver_variante(self, producto, item):
        variantes = producto.variantes_activas
        if not variantes:
            return None, "", 1.0

        variante_id = item.get("variante_id")
        nombre = (item.get("variante_nombre") or "").strip()
        variante = None
        if variante_id:
            variante = next(
                (actual for actual in variantes if actual.id == int(variante_id)), None
            )
        elif nombre:
            variante = next(
                (actual for actual in variantes if actual.nombre.lower() == nombre.lower()),
                None,
            )
        if variante is None:
            raise DatosInvalidosError(
                f"Selecciona un tamaño válido para '{producto.nombre}'."
            )
        return variante, variante.nombre, variante.factor_receta

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

            variante, variante_nombre, factor = self._resolver_variante(producto, item)
            precio_unitario = variante.precio if variante else producto.precio

            almacen_id = producto.almacen_consumo_id
            if almacen_id is None:
                almacen = self.inventario.principal()
                almacen_id = almacen.id

            costo_linea = 0.0
            for ingrediente in producto.receta:
                cantidad_insumo = ingrediente.cantidad * cantidad * factor
                clave = (ingrediente.insumo_id, almacen_id)
                requerimientos[clave] = requerimientos.get(clave, 0.0) + cantidad_insumo
                costo_linea += (
                    ingrediente.cantidad
                    * ingrediente.insumo.costo_unitario
                    * cantidad
                    * factor
                )

            if guisado:
                insumo_guisado = self.insumos.por_codigo(GUISADO_A_INSUMO[guisado])
                if insumo_guisado is None:
                    raise DatosInvalidosError(
                        f"El insumo del guisado '{guisado}' no está configurado en el almacén."
                    )
                cantidad_guisado = PORCION_GUISADO_KG * cantidad * factor
                clave = (insumo_guisado.id, almacen_id)
                requerimientos[clave] = (
                    requerimientos.get(clave, 0.0) + cantidad_guisado
                )
                costo_linea += (
                    PORCION_GUISADO_KG
                    * insumo_guisado.costo_unitario
                    * cantidad
                    * factor
                )

            subtotal = round(precio_unitario * cantidad, 2)
            lineas.append(
                {
                    "producto": producto,
                    "variante": variante,
                    "variante_nombre": variante_nombre,
                    "cantidad": cantidad,
                    "guisado": guisado,
                    "precio_unitario": precio_unitario,
                    "subtotal": subtotal,
                    "costo_linea": round(costo_linea, 2),
                }
            )

        return lineas, requerimientos

    def evaluar_disponibilidad(self, items, turno):
        """Evalúa el pedido línea por línea sin lanzar error por stock.
        Las líneas que no alcanzan se marcan como no disponibles para que
        el POS permita quitarlas y enviar el resto."""
        disponibles = {}
        resultado = []
        for indice, item in enumerate(items):
            try:
                lineas, requerimientos = self._expandir_items([item], turno)
            except DatosInvalidosError as error:
                resultado.append(
                    {
                        "indice": indice,
                        "disponible": False,
                        "motivo": str(error),
                        "producto": "",
                        "cantidad": 0,
                        "variante": "",
                    }
                )
                continue

            linea = lineas[0]
            faltantes = []
            for clave, cantidad in requerimientos.items():
                acumulado = disponibles.get(clave, 0.0) + cantidad
                insumo_id, almacen_id = clave
                stock = self.inventario.stock_de(insumo_id, almacen_id)
                if acumulado > stock + 1e-9:
                    insumo = self.insumos.obtener(insumo_id)
                    faltantes.append(insumo.nombre)

            disponible = not faltantes
            if disponible:
                for clave, cantidad in requerimientos.items():
                    disponibles[clave] = disponibles.get(clave, 0.0) + cantidad

            resultado.append(
                {
                    "indice": indice,
                    "disponible": disponible,
                    "motivo": (
                        "Falta: " + ", ".join(sorted(set(faltantes))) if faltantes else ""
                    ),
                    "producto": linea["producto"].nombre,
                    "cantidad": linea["cantidad"],
                    "variante": linea["variante_nombre"],
                }
            )

        return {
            "lineas": resultado,
            "no_disponibles": sum(1 for linea in resultado if not linea["disponible"]),
        }

    def registrar_venta(
        self,
        mesero_id,
        turno,
        tipo_orden,
        metodo_pago,
        items,
        usuario_id=None,
        mesa_id=None,
        cliente_id=None,
        agregar_a_cuenta=False,
    ):
        if turno not in Turno.TODOS:
            raise DatosInvalidosError("El turno seleccionado no es válido.")
        if tipo_orden not in (TipoOrden.AQUI, TipoOrden.LLEVAR):
            raise DatosInvalidosError("La modalidad de consumo no es válida.")
        if agregar_a_cuenta and not mesa_id:
            raise DatosInvalidosError(
                "Elige la mesa a cuya cuenta se agregará el pedido."
            )
        if not items:
            raise DatosInvalidosError("El pedido no tiene productos. Agrega al menos uno.")

        cliente = None
        if cliente_id:
            cliente = db.session.get(Cliente, int(cliente_id))
            if cliente is None or not cliente.activo:
                raise DatosInvalidosError("El cliente seleccionado no existe o está inactivo.")

        mesa = None
        cuenta = None
        if mesa_id and (tipo_orden == TipoOrden.AQUI or agregar_a_cuenta):
            mesa = self.mesas.obtener(int(mesa_id))
            if mesa is None:
                raise DatosInvalidosError("La mesa seleccionada no existe.")
            if mesa.estado == EstadoMesa.RESERVADA:
                raise DatosInvalidosError(
                    f"La mesa {mesa.numero} está reservada. Elige otra mesa."
                )
            cuenta = self.cuentas.abierta_de(mesa.id)
            if cuenta is None:
                cuenta = CuentaMesa(
                    folio=self.cuentas.siguiente_folio(),
                    mesa_id=mesa.id,
                    abierta_por_id=mesero_id,
                    cliente_id=cliente.id if cliente else None,
                )
                self.cuentas.agregar(cuenta)
                db.session.flush()
            elif cliente is not None:
                if cuenta.cliente_id is None:
                    cuenta.cliente_id = cliente.id
                elif cuenta.cliente_id != cliente.id:
                    raise DatosInvalidosError(
                        "La cuenta ya está asociada a otro cliente. "
                        "Cámbialo desde el detalle de la cuenta."
                    )
            ronda = len(cuenta.ventas) + 1
        else:
            ronda = 1
            if metodo_pago not in MetodoPago.TODOS:
                raise DatosInvalidosError("El método de pago no es válido.")

        lineas, requerimientos = self._expandir_items(items, turno)
        self.inventario.verificar_disponibilidad(requerimientos)

        total = round(sum(linea["subtotal"] for linea in lineas), 2)
        costo_total = round(sum(linea["costo_linea"] for linea in lineas), 2)
        fecha = datetime.now()

        venta = Venta(
            folio=self.ventas.siguiente_folio(),
            turno=turno,
            tipo_orden=tipo_orden,
            metodo_pago=MetodoPago.POR_COBRAR if cuenta else metodo_pago,
            total=total,
            costo_insumos=costo_total,
            mesero_id=mesero_id,
            mesa_id=mesa.id if mesa else None,
            cuenta_id=cuenta.id if cuenta else None,
            cliente_id=cuenta.cliente_id if cuenta else (cliente.id if cliente else None),
            cobrada_en=None if cuenta else fecha,
        )
        for linea in lineas:
            venta.detalles.append(
                VentaDetalle(
                    producto_id=linea["producto"].id,
                    producto_nombre=linea["producto"].nombre,
                    variante_id=linea["variante"].id if linea["variante"] else None,
                    variante_nombre=linea["variante_nombre"],
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
            ronda=ronda,
        )
        self.comandas.agregar(comanda)

        if mesa is not None:
            mesa.estado = EstadoMesa.OCUPADA

        self.inventario.descontar_requerimientos(
            requerimientos, referencia=venta.folio, usuario_id=usuario_id
        )

        if not cuenta:
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
            if venta.cobrada_en is not None:
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
        if venta.cuenta_id is not None:
            return
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
        if mesa.cuenta_abierta is not None and estado in (
            EstadoMesa.LIBRE,
            EstadoMesa.RESERVADA,
        ):
            raise DatosInvalidosError(
                f"La mesa {mesa.numero} tiene una cuenta abierta. Cóbrala antes de liberarla."
            )
        if estado == EstadoMesa.LIBRE and mesa.comandas_activas:
            raise DatosInvalidosError(
                "La mesa tiene comandas activas; no puede marcarse como libre todavía."
            )
        mesa.estado = estado
        db.session.commit()
        return mesa

    def cuenta_de(self, cuenta_id):
        return self.cuentas.obtener(cuenta_id)

    def cuentas_abiertas(self):
        return self.cuentas.abiertas()

    def cuentas_abiertas_por_mesa(self):
        return {cuenta.mesa_id: cuenta for cuenta in self.cuentas.abiertas()}

    def asignar_cliente_cuenta(self, cuenta_id, cliente_id):
        cuenta = self.cuentas.obtener(cuenta_id)
        if cuenta is None:
            raise DatosInvalidosError("La cuenta de mesa indicada no existe.")
        if not cuenta.abierta:
            raise DatosInvalidosError("La cuenta de mesa ya fue cobrada.")
        if cliente_id:
            cliente = db.session.get(Cliente, int(cliente_id))
            if cliente is None or not cliente.activo:
                raise DatosInvalidosError("El cliente seleccionado no existe o está inactivo.")
            cuenta.cliente_id = cliente.id
        else:
            cuenta.cliente_id = None
        db.session.commit()
        return cuenta

    def detalle_cuenta(self, cuenta_id):
        cuenta = self.cuentas.obtener(cuenta_id)
        if cuenta is None:
            return None

        rondas = []
        for indice, venta in enumerate(cuenta.ventas, start=1):
            if venta.cancelada:
                continue
            vigentes = [detalle for detalle in venta.detalles if not detalle.cancelado]
            rondas.append(
                {
                    "numero": venta.comanda.ronda if venta.comanda else indice,
                    "venta": venta,
                    "comanda": venta.comanda,
                    "detalles": venta.detalles,
                    "vigentes": vigentes,
                    "subtotal": venta.total,
                    "articulos": sum(detalle.cantidad for detalle in vigentes),
                }
            )

        comandas_activas = [
            venta.comanda
            for venta in cuenta.ventas_vigentes
            if venta.comanda is not None
            and venta.comanda.estado in (EstadoComanda.EN_PREPARACION, EstadoComanda.LISTA)
        ]
        return {
            "cuenta": cuenta,
            "rondas": rondas,
            "total": cuenta.total,
            "comandas_activas": comandas_activas,
            "puede_cobrar": cuenta.abierta and not comandas_activas,
        }

    def cobrar_cuenta(self, cuenta_id, metodo_pago, usuario_id=None):
        if metodo_pago not in MetodoPago.TODOS:
            raise DatosInvalidosError("El método de pago no es válido.")

        cuenta = self.cuentas.obtener(cuenta_id)
        if cuenta is None:
            raise DatosInvalidosError("La cuenta de mesa indicada no existe.")
        if not cuenta.abierta:
            raise DatosInvalidosError("La cuenta de mesa ya fue cobrada.")

        ventas = cuenta.ventas_vigentes
        pendientes = [
            venta.comanda.folio
            for venta in ventas
            if venta.comanda is not None
            and venta.comanda.estado in (EstadoComanda.EN_PREPARACION, EstadoComanda.LISTA)
        ]
        if pendientes:
            raise DatosInvalidosError(
                "Hay comandas de la mesa todavía en cocina: "
                + ", ".join(pendientes)
                + ". Entrégalas o regístralas como merma antes de cobrar."
            )

        ahora = datetime.now()
        for venta in ventas:
            venta.cobrada_en = ahora
            venta.metodo_pago = metodo_pago
            venta.cliente_id = cuenta.cliente_id
            if venta.total > 0:
                self.contabilidad.registrar_asiento(
                    f"Cobro de cuenta {cuenta.folio} - venta {venta.folio} "
                    f"(ronda {venta.comanda.ronda if venta.comanda else 1})",
                    [
                        (MetodoPago.CUENTA_CONTABLE[metodo_pago], venta.total, 0.0),
                        (CUENTA_VENTAS, 0.0, venta.total),
                    ],
                    origen="VENTA",
                    referencia=venta.folio,
                )
            if venta.comanda is not None and venta.comanda.cerrada_en is None:
                venta.comanda.cerrada_en = ahora
                venta.comanda.cerrada_por_id = usuario_id

        cuenta.cerrada_en = ahora
        cuenta.cerrada_por_id = usuario_id
        cuenta.metodo_pago = metodo_pago
        if cuenta.mesa is not None:
            cuenta.mesa.estado = EstadoMesa.LIMPIEZA

        db.session.commit()
        return cuenta

    def cancelar_detalle(self, detalle_id, motivo, password_admin, usuario_id=None):
        detalle = db.session.get(VentaDetalle, detalle_id)
        if detalle is None:
            raise DatosInvalidosError("El platillo indicado no existe.")
        if detalle.cancelado:
            raise DatosInvalidosError("El platillo ya está cancelado.")

        venta = detalle.venta
        if venta.cuenta_id is None:
            raise DatosInvalidosError(
                "Solo se pueden cancelar platillos de una cuenta de mesa."
            )
        if venta.cobrada_en is not None:
            raise DatosInvalidosError(
                "La cuenta ya fue cobrada. No se puede cancelar el platillo."
            )
        if venta.cancelada:
            raise DatosInvalidosError("La venta ya está cancelada.")
        comanda = venta.comanda
        if comanda is None:
            raise DatosInvalidosError("El platillo no tiene comanda asociada.")

        autorizador = None
        for usuario in self.usuarios.activos():
            if usuario.es_admin and usuario.verificar_password(password_admin or ""):
                autorizador = usuario
                break
        if autorizador is None:
            raise DatosInvalidosError(
                "Se requiere la contraseña de un administrador para cancelar "
                "un platillo ya enviado a cocina."
            )

        detalle.cancelado = True
        detalle.cancelado_en = datetime.now()
        detalle.motivo_cancelacion = (motivo or "Cancelado por el cliente").strip()
        detalle.cancelado_por_id = usuario_id
        detalle.autorizado_por_id = autorizador.id

        venta.total = round(
            sum(linea.subtotal for linea in venta.detalles if not linea.cancelado), 2
        )

        cancelacion = CancelacionPlatillo(
            detalle_id=detalle.id,
            comanda_id=comanda.id,
            motivo=detalle.motivo_cancelacion,
            cancelado_por_id=usuario_id,
            autorizado_por_id=autorizador.id,
        )
        self.cancelaciones.agregar(cancelacion)
        db.session.commit()
        return cancelacion

    def cancelaciones_pendientes(self):
        return self.cancelaciones.pendientes()

    def marcar_cancelacion_atendida(self, cancelacion_id, usuario_id=None):
        cancelacion = self.cancelaciones.obtener(cancelacion_id)
        if cancelacion is None:
            raise DatosInvalidosError("La cancelación indicada no existe.")
        if cancelacion.atendida_en is not None:
            raise DatosInvalidosError("La cancelación ya fue atendida por cocina.")
        cancelacion.atendida_en = datetime.now()
        cancelacion.atendida_por_id = usuario_id
        db.session.commit()
        return cancelacion

    def detalle_comanda(self, comanda_id):
        comanda = self.comandas.obtener(comanda_id)
        if comanda is None:
            return None

        requerimientos = {}
        lineas = []
        for detalle in comanda.venta.detalles:
            if detalle.cancelado:
                lineas.append({"detalle": detalle, "ingredientes": []})
                continue
            producto = detalle.producto
            almacen_id = producto.almacen_consumo_id
            factor = (
                detalle.variante.factor_receta
                if detalle.variante is not None
                else 1.0
            )
            ingredientes = []
            for ingrediente in producto.receta:
                cantidad = ingrediente.cantidad * detalle.cantidad * factor
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
                    cantidad = PORCION_GUISADO_KG * detalle.cantidad * factor
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
