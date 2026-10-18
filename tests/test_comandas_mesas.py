import json

from app.extensions import db
from app.models.contabilidad import Asiento
from app.models.inventario import Insumo, StockAlmacen
from app.models.ventas import Comanda, Mesa, Venta
from app.repositories.venta_repository import VentaRepositorio
from tests.conftest import iniciar_sesion, insumo_id, producto_id


def _confirmar(client, items, turno="MANANA", tipo="AQUI", metodo="EFECTIVO", mesa_id=None):
    datos = {
        "turno": turno,
        "tipo_orden": tipo,
        "metodo_pago": metodo,
        "items_json": json.dumps(items),
    }
    if mesa_id is not None:
        datos["mesa_id"] = str(mesa_id)
    return client.post("/pos/confirmar", data=datos, follow_redirects=True)


def _ultima_comanda():
    return Comanda.query.order_by(Comanda.id.desc()).first()


def _crear_venta(client, producto_codigo="BEB-CAF-AM", cantidad=1, mesa_id=None):
    with client.application.app_context():
        codigo = producto_id(producto_codigo)
    return _confirmar(client, [{"producto_id": codigo, "cantidad": cantidad}], mesa_id=mesa_id)


def test_venta_con_mesa_ocupa_mesa_y_cierre_la_manda_a_limpieza(mesero_logueado, app):
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
        comanda_id = comanda.id

    iniciar_sesion(client, "chef1", "chef123")
    client.post(f"/cocina/comanda/{comanda_id}/listo", follow_redirects=True)
    client.post(f"/cocina/comanda/{comanda_id}/entregar", follow_redirects=True)

    iniciar_sesion(client, "mesero1", "mesero123")
    respuesta = client.post(f"/pos/comanda/{comanda_id}/cerrar", follow_redirects=True)
    assert respuesta.status_code == 200

    with app.app_context():
        comanda = db.session.get(Comanda, comanda_id)
        assert comanda.cerrada_en is not None
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

        almacen = Almacen.query.filter_by(codigo="ALM-POS").first()
        stock = StockAlmacen.query.filter_by(insumo_id=vaso.id, almacen_id=almacen.id).first()
        stock.cantidad = 0.0
        db.session.commit()

    texto = client.get(f"/pos/comanda/{comanda_id}").get_data(as_text=True)
    assert "Se vació el inventario" in texto
    assert "AGOTADO" in texto


def test_cambio_estado_mesa_con_comandas_activas(mesero_logueado, app):
    client = mesero_logueado
    with app.app_context():
        mesa = Mesa.query.filter_by(estado="LIBRE").first()
        mesa_id = mesa.id
        cafe_id = producto_id("BEB-CAF-AM")

    _confirmar(client, [{"producto_id": cafe_id, "cantidad": 1}], mesa_id=mesa_id)

    respuesta = client.post(
        f"/pos/mesas/{mesa_id}/estado", data={"estado": "LIBRE"}, follow_redirects=True
    )
    assert "comandas activas" in respuesta.get_data(as_text=True)

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
        client, [{"producto_id": jamaica_id, "cantidad": 1}], turno="TARDE"
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
