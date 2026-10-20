import json
from datetime import datetime, timedelta

from app.extensions import db
from app.models.contabilidad import Asiento
from app.models.inventario import Insumo, StockAlmacen
from app.models.ventas import (
    CancelacionPlatillo,
    Comanda,
    CuentaMesa,
    Mesa,
    Venta,
    VentaDetalle,
)
from app.repositories.venta_repository import VentaRepositorio
from tests.conftest import iniciar_sesion, insumo_id, producto_id, usuario_id


def _confirmar(client, items, turno="MANANA", tipo="AQUI", metodo="EFECTIVO", mesa_id=None, **extra):
    datos = {
        "turno": turno,
        "tipo_orden": tipo,
        "metodo_pago": metodo,
        "items_json": json.dumps(items),
    }
    if mesa_id is not None:
        datos["mesa_id"] = str(mesa_id)
    datos.update(extra)
    return client.post("/pos/confirmar", data=datos, follow_redirects=True)


def _ultima_comanda():
    return Comanda.query.order_by(Comanda.id.desc()).first()


def _crear_venta(client, producto_codigo="BEB-CAF-AM", cantidad=1, mesa_id=None):
    with client.application.app_context():
        codigo = producto_id(producto_codigo)
    return _confirmar(client, [{"producto_id": codigo, "cantidad": cantidad}], mesa_id=mesa_id)


def test_venta_con_mesa_abre_cuenta_y_cobro_la_manda_a_limpieza(mesero_logueado, app):
    client = mesero_logueado
    with app.app_context():
        mesa = Mesa.query.filter_by(estado="LIBRE").first()
        mesa_id = mesa.id
        cafe_id = producto_id("BEB-CAF-AM")

    _confirmar(client, [{"producto_id": cafe_id, "cantidad": 1}], mesa_id=mesa_id)

    with app.app_context():
        assert db.session.get(Mesa, mesa_id).estado == "OCUPADA"
        comanda = _ultima_comanda()
        assert comanda.venta.mesa_id == mesa_id
        assert comanda.venta.por_cobrar is True
        assert comanda.venta.metodo_pago == "POR_COBRAR"
        assert comanda.venta.cuenta_id is not None
        comanda_id = comanda.id
        venta_id = comanda.venta_id
        cuenta_id = comanda.venta.cuenta_id

    iniciar_sesion(client, "chef1", "chef123")
    client.post(f"/cocina/comanda/{comanda_id}/listo", follow_redirects=True)
    client.post(f"/cocina/comanda/{comanda_id}/entregar", follow_redirects=True)

    iniciar_sesion(client, "mesero1", "mesero123")
    respuesta = client.post(f"/pos/comanda/{comanda_id}/cerrar", follow_redirects=True)
    assert respuesta.status_code == 200

    with app.app_context():
        comanda = db.session.get(Comanda, comanda_id)
        assert comanda.cerrada_en is not None
        assert db.session.get(Mesa, mesa_id).estado == "OCUPADA"
        assert db.session.get(Venta, venta_id).por_cobrar is True

    respuesta = client.post(
        f"/pos/cuenta/{cuenta_id}/cobrar",
        data={"metodo_pago": "EFECTIVO"},
        follow_redirects=True,
    )
    assert "Cuenta cobrada" in respuesta.get_data(as_text=True)

    with app.app_context():
        venta = db.session.get(Venta, venta_id)
        assert venta.cobrada_en is not None
        assert venta.metodo_pago == "EFECTIVO"
        cuenta = db.session.get(CuentaMesa, cuenta_id)
        assert cuenta.cerrada_en is not None
        assert cuenta.metodo_pago == "EFECTIVO"
        assert db.session.get(Mesa, mesa_id).estado == "LIMPIEZA"


def test_cerrar_comanda_en_preparacion_es_rechazado(mesero_logueado, app):
    client = mesero_logueado
    _crear_venta(client)

    with app.app_context():
        comanda_id = _ultima_comanda().id

    respuesta = client.post(f"/pos/comanda/{comanda_id}/cerrar", follow_redirects=True)
    assert "todavía no se entrega" in respuesta.get_data(as_text=True)

    estado = client.get("/pos/comandas-estado").get_json()
    fila = next(f for f in estado if f["id"] == comanda_id)
    assert fila["cerrable"] is False
    assert fila["estado"] == "EN_PREPARACION"


def test_comandas_estado_json_refleja_entrega(mesero_logueado, app):
    client = mesero_logueado
    _crear_venta(client)

    with app.app_context():
        comanda_id = _ultima_comanda().id

    iniciar_sesion(client, "chef1", "chef123")
    firma_antes = client.get("/cocina/pulso").get_json()["firma"]
    assert f"{comanda_id}:EN_PREPARACION" in firma_antes

    client.post(f"/cocina/comanda/{comanda_id}/entregar", follow_redirects=True)
    firma_despues = client.get("/cocina/pulso").get_json()["firma"]
    assert firma_despues != firma_antes
    assert f"{comanda_id}:EN_PREPARACION" not in firma_despues

    iniciar_sesion(client, "mesero1", "mesero123")
    fila = next(f for f in client.get("/pos/comandas-estado").get_json() if f["id"] == comanda_id)
    assert fila["estado"] == "ENTREGADA"
    assert fila["cerrable"] is True
    assert fila["etiqueta"] == "Entregada"


def test_merma_conservando_venta_registra_asiento_y_permite_cerrar(mesero_logueado, app):
    client = mesero_logueado
    _crear_venta(client)

    with app.app_context():
        asientos_antes = Asiento.query.count()
        comanda = _ultima_comanda()
        comanda_id = comanda.id
        folio_venta = comanda.venta.folio

    iniciar_sesion(client, "chef1", "chef123")
    respuesta = client.post(
        f"/cocina/comanda/{comanda_id}/merma",
        data={"motivo": "Cliente no pasó por su platillo"},
        follow_redirects=True,
    )
    assert "merma" in respuesta.get_data(as_text=True)

    with app.app_context():
        comanda = db.session.get(Comanda, comanda_id)
        assert comanda.estado == "MERMA"
        assert comanda.motivo_merma == "Cliente no pasó por su platillo"
        assert comanda.venta.cancelada is False
        assert Asiento.query.count() == asientos_antes + 1
        asiento = Asiento.query.order_by(Asiento.id.desc()).first()
        assert asiento.origen == "MERMA"
        assert asiento.referencia == folio_venta

    iniciar_sesion(client, "mesero1", "mesero123")
    respuesta = client.post(f"/pos/comanda/{comanda_id}/cerrar", follow_redirects=True)
    assert respuesta.status_code == 200
    with app.app_context():
        assert db.session.get(Comanda, comanda_id).cerrada_en is not None


def test_merma_cancelando_venta_la_excluye_de_los_reportes(mesero_logueado, app):
    client = mesero_logueado
    _crear_venta(client)

    with app.app_context():
        comanda = _ultima_comanda()
        comanda_id = comanda.id
        venta_id = comanda.venta_id

    iniciar_sesion(client, "chef1", "chef123")
    client.post(
        f"/cocina/comanda/{comanda_id}/merma",
        data={"motivo": "Cliente canceló el pedido", "cancelar_venta": "1"},
        follow_redirects=True,
    )

    with app.app_context():
        venta = db.session.get(Venta, venta_id)
        assert venta.cancelada is True
        assert venta.cancelada_en is not None
        assert venta.motivo_cancelacion == "Cliente canceló el pedido"
        asiento = Asiento.query.order_by(Asiento.id.desc()).first()
        assert asiento.origen == "CANCELACION"
        assert venta not in VentaRepositorio().recientes(50)

    with app.app_context():
        from datetime import datetime as dt
        from datetime import timedelta

        from app.services.reporte_service import ReporteService

        resumen = ReporteService().resumen(dt.now() - timedelta(days=1), dt.now())
        assert all(v.cancelada is False for v in resumen["ventas"])
        assert resumen["total"] == round(sum(v.total for v in resumen["ventas"]), 2)
        assert venta_id not in [v.id for v in resumen["ventas"]]

    iniciar_sesion(client, "admin", "admin123")
    respuesta = client.get("/reportes/")
    texto = respuesta.get_data(as_text=True)
    assert "Ventas del periodo" in texto


def test_avisar_faltante_es_idempotente_y_resoluble(chef_logueado, app):
    client = chef_logueado
    with app.app_context():
        insumo = insumo_id("INS-GUI-BAR")

    client.post(f"/cocina/insumos/{insumo}/avisar", follow_redirects=True)
    client.post(f"/cocina/insumos/{insumo}/avisar", follow_redirects=True)

    with app.app_context():
        from app.models.inventario import AvisoFaltante

        avisos = AvisoFaltante.query.filter_by(insumo_id=insumo, resuelto=False).all()
        assert len(avisos) == 1
        aviso_id = avisos[0].id

    texto = client.get("/cocina/insumos").get_data(as_text=True)
    assert "avisado" in texto

    client.post(f"/cocina/insumos/aviso/{aviso_id}/resolver", follow_redirects=True)
    with app.app_context():
        from app.models.inventario import AvisoFaltante

        assert db.session.get(AvisoFaltante, aviso_id).resuelto is True

    texto = client.get("/cocina/").get_data(as_text=True)
    assert "reportados como faltantes" not in texto


def test_detalle_comanda_reporta_insumos_agotados(mesero_logueado, app):
    client = mesero_logueado
    _crear_venta(client)

    with app.app_context():
        comanda_id = _ultima_comanda().id
        vaso = db.session.get(Insumo, insumo_id("INS-V12"))
        from app.models.inventario import Almacen

        almacen = Almacen.query.filter_by(codigo="ALM-MP").first()
        stock = StockAlmacen.query.filter_by(insumo_id=vaso.id, almacen_id=almacen.id).first()
        stock.cantidad = 0.0
        db.session.commit()

    texto = client.get(f"/pos/comanda/{comanda_id}").get_data(as_text=True)
    assert "Se vació el inventario" in texto
    assert "AGOTADO" in texto


def test_cambio_estado_mesa_bloqueado_por_cuenta_abierta(mesero_logueado, app):
    client = mesero_logueado
    with app.app_context():
        mesa = Mesa.query.filter_by(estado="LIBRE").first()
        mesa_id = mesa.id
        cafe_id = producto_id("BEB-CAF-AM")

    _confirmar(client, [{"producto_id": cafe_id, "cantidad": 1}], mesa_id=mesa_id)

    with app.app_context():
        comanda = _ultima_comanda()
        comanda_id = comanda.id
        cuenta_id = comanda.venta.cuenta_id

    respuesta = client.post(
        f"/pos/mesas/{mesa_id}/estado", data={"estado": "LIBRE"}, follow_redirects=True
    )
    assert "cuenta abierta" in respuesta.get_data(as_text=True)

    respuesta = client.post(
        f"/pos/mesas/{mesa_id}/estado", data={"estado": "RESERVADA"}, follow_redirects=True
    )
    assert "cuenta abierta" in respuesta.get_data(as_text=True)

    with app.app_context():
        assert db.session.get(Mesa, mesa_id).estado == "OCUPADA"

    iniciar_sesion(client, "chef1", "chef123")
    client.post(f"/cocina/comanda/{comanda_id}/listo", follow_redirects=True)
    client.post(f"/cocina/comanda/{comanda_id}/entregar", follow_redirects=True)
    iniciar_sesion(client, "mesero1", "mesero123")
    client.post(f"/pos/comanda/{comanda_id}/cerrar", follow_redirects=True)
    client.post(
        f"/pos/cuenta/{cuenta_id}/cobrar",
        data={"metodo_pago": "TARJETA"},
        follow_redirects=True,
    )

    respuesta = client.post(
        f"/pos/mesas/{mesa_id}/estado", data={"estado": "RESERVADA"}, follow_redirects=True
    )
    assert "Reservada" in respuesta.get_data(as_text=True)

    with app.app_context():
        assert db.session.get(Mesa, mesa_id).estado == "RESERVADA"


def test_bebidas_de_tarde_disponibles_en_pos(mesero_logueado, app):
    client = mesero_logueado
    with app.app_context():
        jamaica_id = producto_id("TAR-AGU-JAM")

    respuesta = _confirmar(
        client,
        [
            {
                "producto_id": jamaica_id,
                "cantidad": 1,
                "variante_nombre": "Litro",
            }
        ],
        turno="TARDE",
    )
    assert "registrada" in respuesta.get_data(as_text=True)

    texto = client.get("/pos/?turno=TARDE").get_data(as_text=True)
    assert "Agua de Jamaica" in texto
    assert "Sangría" in texto


def test_accesos_a_mesas(mesero_logueado):
    assert mesero_logueado.get("/pos/mesas").status_code == 200
    assert mesero_logueado.get("/reportes/").status_code == 403


def test_accesos_de_chef(chef_logueado):
    assert chef_logueado.get("/reportes/").status_code == 403
    assert chef_logueado.get("/pos/").status_code == 403


def _cuenta_abierta():
    return (
        CuentaMesa.query.filter(CuentaMesa.cerrada_en.is_(None))
        .order_by(CuentaMesa.id.desc())
        .first()
    )


def test_rondas_se_acumulan_y_solo_se_reportan_al_cobrar(mesero_logueado, app):
    client = mesero_logueado
    with app.app_context():
        mesa = Mesa.query.filter_by(estado="LIBRE").first()
        mesa_id = mesa.id
        cafe_id = producto_id("BEB-CAF-AM")
        pan_id = producto_id("PAN-CONCHA")

    _confirmar(client, [{"producto_id": cafe_id, "cantidad": 1}], mesa_id=mesa_id)
    _confirmar(client, [{"producto_id": pan_id, "cantidad": 2}], mesa_id=mesa_id)

    with app.app_context():
        cuentas = CuentaMesa.query.all()
        assert len(cuentas) == 1
        cuenta = cuentas[0]
        assert cuenta.abierta is True
        assert cuenta.rondas == 2
        assert [venta.comanda.ronda for venta in cuenta.ventas] == [1, 2]
        assert all(venta.por_cobrar for venta in cuenta.ventas)
        assert all(venta.cobrada_en is None for venta in cuenta.ventas)
        total_cuenta = cuenta.total
        cuenta_id = cuenta.id
        venta_ids = [venta.id for venta in cuenta.ventas]
        folios = [venta.folio for venta in cuenta.ventas]
        asientos_antes = Asiento.query.filter(Asiento.referencia.in_(folios)).count()

        desde = datetime.now() - timedelta(hours=2)
        hasta = datetime.now() + timedelta(hours=2)
        from app.services.reporte_service import ReporteService

        resumen_antes = ReporteService().resumen(desde, hasta)
        assert not any(venta.id in venta_ids for venta in resumen_antes["ventas"])

        texto = client.get(f"/pos/cuenta/{cuenta_id}").get_data(as_text=True)
        assert "Ronda 1" in texto
        assert "Ronda 2" in texto
        assert "ADICIÓN" in texto

        texto_mesas = client.get("/pos/mesas").get_data(as_text=True)
        assert "Cobrar y liberar mesa" in texto_mesas
        assert "Agregar ronda" in texto_mesas

        texto_pos = client.get(f"/pos/?mesa={mesa_id}").get_data(as_text=True)
        assert "tiene una cuenta abierta" in texto_pos

        texto_ticket = client.get(f"/pos/cuenta/{cuenta_id}/ticket").get_data(as_text=True)
        assert "Ronda 1" in texto_ticket
        assert "Por cobrar" in texto_ticket

    iniciar_sesion(client, "chef1", "chef123")
    texto_cocina = client.get("/cocina/").get_data(as_text=True)
    assert "RONDA 1" in texto_cocina
    assert "RONDA 2" in texto_cocina
    assert "ADICIÓN" in texto_cocina

    with app.app_context():
        comandas = Comanda.query.filter(Comanda.venta_id.in_(venta_ids)).all()
        comanda_ids = [comanda.id for comanda in comandas]
    for comanda_id in comanda_ids:
        client.post(f"/cocina/comanda/{comanda_id}/listo", follow_redirects=True)
        client.post(f"/cocina/comanda/{comanda_id}/entregar", follow_redirects=True)

    iniciar_sesion(client, "mesero1", "mesero123")
    for comanda_id in comanda_ids:
        client.post(f"/pos/comanda/{comanda_id}/cerrar", follow_redirects=True)

    respuesta = client.post(
        f"/pos/cuenta/{cuenta_id}/cobrar",
        data={"metodo_pago": "EFECTIVO"},
        follow_redirects=True,
    )
    assert "Cuenta cobrada" in respuesta.get_data(as_text=True)

    texto_ticket = client.get(f"/pos/cuenta/{cuenta_id}/ticket").get_data(as_text=True)
    assert "Efectivo" in texto_ticket
    assert "Por cobrar" not in texto_ticket

    with app.app_context():
        from app.services.reporte_service import ReporteService

        resumen_despues = ReporteService().resumen(desde, hasta)
        incluidas = [v for v in resumen_despues["ventas"] if v.id in venta_ids]
        assert len(incluidas) == 2
        assert round(sum(venta.total for venta in incluidas), 2) == total_cuenta
        assert all(venta.metodo_pago == "EFECTIVO" for venta in incluidas)
        assert all(venta.cobrada_en is not None for venta in incluidas)
        assert Asiento.query.filter(Asiento.referencia.in_(folios)).count() == asientos_antes + 2


def test_ronda_para_llevar_se_carga_a_la_cuenta_de_la_mesa(mesero_logueado, app):
    client = mesero_logueado
    with app.app_context():
        mesa = Mesa.query.filter_by(estado="LIBRE").first()
        mesa_id = mesa.id
        cafe_id = producto_id("BEB-CAF-AM")
        pan_id = producto_id("PAN-CONCHA")

    _confirmar(client, [{"producto_id": cafe_id, "cantidad": 1}], mesa_id=mesa_id)
    respuesta = _confirmar(
        client,
        [{"producto_id": pan_id, "cantidad": 2}],
        tipo="LLEVAR",
        mesa_id=mesa_id,
        agregar_a_cuenta="1",
    )
    assert "Ronda 2 agregada a la cuenta" in respuesta.get_data(as_text=True)

    with app.app_context():
        cuenta = CuentaMesa.query.filter(CuentaMesa.cerrada_en.is_(None)).one()
        assert cuenta.rondas == 2
        assert cuenta.ventas[1].tipo_orden == "LLEVAR"
        assert cuenta.ventas[1].mesa_id == mesa_id
        assert cuenta.ventas[1].metodo_pago == "POR_COBRAR"
        assert cuenta.ventas[1].comanda.tipo_orden == "LLEVAR"
        assert cuenta.ventas[1].comanda.ronda == 2
        cuenta_id = cuenta.id
        comandas = [ronda.comanda for ronda in cuenta.ventas]

    texto_cuenta = client.get(f"/pos/cuenta/{cuenta_id}").get_data(as_text=True)
    assert "Para llevar" in texto_cuenta
    texto_ticket = client.get(f"/pos/cuenta/{cuenta_id}/ticket").get_data(as_text=True)
    assert "Para llevar" in texto_ticket

    iniciar_sesion(client, "chef1", "chef123")
    for comanda in comandas:
        client.post(f"/cocina/comanda/{comanda.id}/listo", follow_redirects=True)
        client.post(f"/cocina/comanda/{comanda.id}/entregar", follow_redirects=True)

    iniciar_sesion(client, "mesero1", "mesero123")
    respuesta = client.post(
        f"/pos/cuenta/{cuenta_id}/cobrar",
        data={"metodo_pago": "EFECTIVO"},
        follow_redirects=True,
    )
    assert respuesta.status_code == 200
    assert "Cuenta cobrada" in respuesta.get_data(as_text=True)

    with app.app_context():
        cuenta = db.session.get(CuentaMesa, cuenta_id)
        assert cuenta.cerrada_en is not None
        assert db.session.get(Mesa, mesa_id).estado == "LIMPIEZA"
        assert all(venta.cobrada_en is not None for venta in cuenta.ventas)


def test_cuenta_inexistente_redirige_a_mesas(mesero_logueado):
    client = mesero_logueado
    for ruta in ("/pos/cuenta/999999", "/pos/cuenta/999999/ticket"):
        respuesta = client.get(ruta)
        assert respuesta.status_code == 302
        assert "/pos/mesas" in respuesta.headers["Location"]


def test_pos_genera_accion_correcta_para_cerrar_comanda_en_tarjeta(mesero_logueado):
    html = mesero_logueado.get("/pos/").get_data(as_text=True)
    assert 'window.URL_CERRAR_COMANDA = "/pos/comanda/999999/cerrar";' in html
    assert 'window.URL_CERRAR_COMANDA.replace("999999", comanda.id)' in html
    assert 'window.URL_CERRAR_COMANDA + comanda.id' not in html


def test_no_se_puede_cobrar_con_comandas_en_cocina(mesero_logueado, app):
    client = mesero_logueado
    with app.app_context():
        mesa = Mesa.query.filter_by(estado="LIBRE").first()
        mesa_id = mesa.id
        cafe_id = producto_id("BEB-CAF-AM")

    _confirmar(client, [{"producto_id": cafe_id, "cantidad": 1}], mesa_id=mesa_id)

    with app.app_context():
        cuenta_id = _cuenta_abierta().id

    respuesta = client.post(
        f"/pos/cuenta/{cuenta_id}/cobrar",
        data={"metodo_pago": "EFECTIVO"},
        follow_redirects=True,
    )
    assert "todavía en cocina" in respuesta.get_data(as_text=True)

    with app.app_context():
        cuenta = db.session.get(CuentaMesa, cuenta_id)
        assert cuenta.abierta is True
        assert all(venta.por_cobrar for venta in cuenta.ventas)
        assert db.session.get(Mesa, mesa_id).estado == "OCUPADA"


def test_cancelar_platillo_requiere_password_admin_y_avisa_cocina(mesero_logueado, app):
    client = mesero_logueado
    with app.app_context():
        mesa = Mesa.query.filter_by(estado="LIBRE").first()
        mesa_id = mesa.id
        cafe_id = producto_id("BEB-CAF-AM")
        pan_id = producto_id("PAN-CONCHA")

    _confirmar(
        client,
        [
            {"producto_id": cafe_id, "cantidad": 1},
            {"producto_id": pan_id, "cantidad": 2},
        ],
        mesa_id=mesa_id,
    )

    with app.app_context():
        cuenta = _cuenta_abierta()
        venta = cuenta.ventas[0]
        detalle = next(linea for linea in venta.detalles if linea.producto_id == pan_id)
        detalle_id = detalle.id
        subtotal_pan = detalle.subtotal
        total_original = venta.total
        cuenta_id = cuenta.id

    url = f"/pos/detalle/{detalle_id}/cancelar"
    volver = f"/pos/cuenta/{cuenta_id}"

    respuesta = client.post(
        url,
        data={"motivo": "Cliente cambió de opinión", "password_admin": "", "volver": volver},
        follow_redirects=True,
    )
    assert "contraseña de un administrador" in respuesta.get_data(as_text=True)

    respuesta = client.post(
        url,
        data={
            "motivo": "Cliente cambió de opinión",
            "password_admin": "clave-incorrecta",
            "volver": volver,
        },
        follow_redirects=True,
    )
    assert "contraseña de un administrador" in respuesta.get_data(as_text=True)

    with app.app_context():
        detalle = db.session.get(VentaDetalle, detalle_id)
        assert detalle.cancelado is False
        assert db.session.get(Venta, detalle.venta_id).total == total_original

    respuesta = client.post(
        url,
        data={
            "motivo": "Cliente cambió de opinión",
            "password_admin": "admin123",
            "volver": volver,
        },
        follow_redirects=True,
    )
    assert "Platillo cancelado" in respuesta.get_data(as_text=True)

    with app.app_context():
        detalle = db.session.get(VentaDetalle, detalle_id)
        assert detalle.cancelado is True
        assert detalle.autorizado_por.username == "admin"
        venta = db.session.get(Venta, detalle.venta_id)
        assert venta.total == round(total_original - subtotal_pan, 2)
        cancelacion = CancelacionPlatillo.query.one()
        assert cancelacion.pendiente is True
        assert cancelacion.detalle_id == detalle_id
        assert cancelacion.autorizado_por.username == "admin"
        cancelacion_id = cancelacion.id
        cuenta = db.session.get(CuentaMesa, cuenta_id)
        assert cuenta.total == venta.total

    iniciar_sesion(client, "chef1", "chef123")
    texto = client.get("/cocina/").get_data(as_text=True)
    assert "Cancelaciones autorizadas" in texto
    assert "Cliente cambió de opinión" in texto

    client.post(f"/cocina/cancelacion/{cancelacion_id}/enterado", follow_redirects=True)
    with app.app_context():
        cancelacion = db.session.get(CancelacionPlatillo, cancelacion_id)
        assert cancelacion.atendida_en is not None
        assert cancelacion.atendida_por.username == "chef1"

    texto = client.get("/cocina/").get_data(as_text=True)
    assert "Cancelaciones autorizadas" not in texto


def test_merma_de_ronda_cancelada_no_libera_mesa_ni_suma_al_total(mesero_logueado, app):
    client = mesero_logueado
    with app.app_context():
        mesa = Mesa.query.filter_by(estado="LIBRE").first()
        mesa_id = mesa.id
        cafe_id = producto_id("BEB-CAF-AM")
        pan_id = producto_id("PAN-CONCHA")

    _confirmar(client, [{"producto_id": cafe_id, "cantidad": 1}], mesa_id=mesa_id)
    with app.app_context():
        comanda_cancelada_id = _ultima_comanda().id

    _confirmar(client, [{"producto_id": pan_id, "cantidad": 1}], mesa_id=mesa_id)
    with app.app_context():
        comanda_vigente_id = _ultima_comanda().id
        cuenta = _cuenta_abierta()
        cuenta_id = cuenta.id
        venta_cancelada_id = cuenta.ventas[0].id
        total_esperado = cuenta.ventas[1].total

    iniciar_sesion(client, "chef1", "chef123")
    client.post(
        f"/cocina/comanda/{comanda_cancelada_id}/merma",
        data={"motivo": "Cliente canceló el pedido", "cancelar_venta": "1"},
        follow_redirects=True,
    )

    with app.app_context():
        venta = db.session.get(Venta, venta_cancelada_id)
        assert venta.cancelada is True
        assert venta.cobrada_en is None
        assert Asiento.query.filter_by(origen="CANCELACION").count() == 0
        cuenta = db.session.get(CuentaMesa, cuenta_id)
        assert cuenta.abierta is True
        assert cuenta.total == total_esperado
        assert db.session.get(Mesa, mesa_id).estado == "OCUPADA"

    client.post(f"/cocina/comanda/{comanda_vigente_id}/listo", follow_redirects=True)
    client.post(f"/cocina/comanda/{comanda_vigente_id}/entregar", follow_redirects=True)

    iniciar_sesion(client, "mesero1", "mesero123")
    client.post(f"/pos/comanda/{comanda_vigente_id}/cerrar", follow_redirects=True)
    respuesta = client.post(
        f"/pos/cuenta/{cuenta_id}/cobrar",
        data={"metodo_pago": "TRANSFERENCIA"},
        follow_redirects=True,
    )
    assert "Cuenta cobrada" in respuesta.get_data(as_text=True)

    with app.app_context():
        assert db.session.get(Venta, venta_cancelada_id).cobrada_en is None
        cuenta = db.session.get(CuentaMesa, cuenta_id)
        assert cuenta.cerrada_en is not None
        assert db.session.get(Mesa, mesa_id).estado == "LIMPIEZA"


def test_venta_para_llevar_sigue_cobrada_de_inmediato(mesero_logueado, app):
    client = mesero_logueado
    with app.app_context():
        cafe_id = producto_id("BEB-CAF-AM")

    _confirmar(
        client,
        [{"producto_id": cafe_id, "cantidad": 1}],
        tipo="LLEVAR",
        metodo="TARJETA",
    )

    with app.app_context():
        venta = _ultima_comanda().venta
        assert venta.cuenta_id is None
        assert venta.cobrada_en is not None
        assert venta.por_cobrar is False
        assert venta.metodo_pago == "TARJETA"


def test_migracion_marca_solo_ventas_historicas_como_cobradas(app):
    from app.constants import MetodoPago, TipoOrden, Turno
    from app.migraciones import aplicar_migraciones

    with app.app_context():
        mesero = usuario_id("mesero1")
        mesa = Mesa.query.first()
        historica = Venta(
            folio="VTA-HIST",
            fecha=datetime.now(),
            turno=Turno.MANANA,
            tipo_orden=TipoOrden.LLEVAR,
            metodo_pago=MetodoPago.EFECTIVO,
            total=10.0,
            costo_insumos=0.0,
            mesero_id=mesero,
        )
        cuenta = CuentaMesa(
            folio="CTA-TEST", mesa_id=mesa.id, abierta_por_id=mesero
        )
        db.session.add_all([historica, cuenta])
        db.session.flush()
        ronda = Venta(
            folio="VTA-RONDA",
            fecha=datetime.now(),
            turno=Turno.MANANA,
            tipo_orden=TipoOrden.AQUI,
            metodo_pago=MetodoPago.POR_COBRAR,
            total=20.0,
            costo_insumos=0.0,
            mesero_id=mesero,
            mesa_id=mesa.id,
            cuenta_id=cuenta.id,
        )
        db.session.add(ronda)
        db.session.commit()

        aplicar_migraciones()

        assert historica.cobrada_en is not None
        assert ronda.cobrada_en is None
        assert ronda.por_cobrar is True
