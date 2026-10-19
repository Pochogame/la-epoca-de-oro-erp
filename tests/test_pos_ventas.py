import json

from app.extensions import db
from app.models.ventas import Comanda, Venta
from tests.conftest import (
    iniciar_sesion,
    insumo_id,
    producto_id,
    stock_insumo,
)


def _confirmar(client, items, turno="MANANA", tipo="AQUI", metodo="EFECTIVO"):
    return client.post(
        "/pos/confirmar",
        data={
            "turno": turno,
            "tipo_orden": tipo,
            "metodo_pago": metodo,
            "items_json": json.dumps(items),
        },
        follow_redirects=True,
    )


def test_venta_descuenta_inventario_y_genera_comanda(mesero_logueado, app):
    client = mesero_logueado

    with app.app_context():
        stock_vasos_antes = stock_insumo("INS-V12")
        ventas_antes = Venta.query.count()
        cafe_id = producto_id("BEB-CAF-AM")

    respuesta = _confirmar(client, [{"producto_id": cafe_id, "cantidad": 2}])
    texto = respuesta.get_data(as_text=True)
    assert "Ticket" in texto or "La Época de Oro" in texto

    with app.app_context():
        assert Venta.query.count() == ventas_antes + 1
        venta = Venta.query.order_by(Venta.id.desc()).first()
        assert venta.total == 70.0
        assert venta.costo_insumos > 0
        assert venta.comanda is not None
        assert venta.comanda.estado == "EN_PREPARACION"
        assert stock_insumo("INS-V12") == stock_vasos_antes - 2


def test_venta_sin_stock_es_rechazada(mesero_logueado, app):
    client = mesero_logueado
    with app.app_context():
        from app.models.inventario import Insumo

        concha = Insumo.query.filter_by(codigo="INS-PCO").first()
        for stock in concha.stocks:
            stock.cantidad = 0.0
        db.session.commit()
        ventas_antes = Venta.query.count()
        concha_id = producto_id("PAN-CONCHA")

    respuesta = _confirmar(client, [{"producto_id": concha_id, "cantidad": 1}])
    texto = respuesta.get_data(as_text=True)
    assert "No hay stock suficiente" in texto

    with app.app_context():
        assert Venta.query.count() == ventas_antes


def test_taco_requiere_guisado_valido(mesero_logueado, app):
    client = mesero_logueado
    with app.app_context():
        taco_id = producto_id("TAR-TACOS")

    respuesta = _confirmar(
        client, [{"producto_id": taco_id, "cantidad": 1, "guisado": ""}], turno="TARDE"
    )
    assert "guisado válido" in respuesta.get_data(as_text=True)

    respuesta = _confirmar(
        client,
        [{"producto_id": taco_id, "cantidad": 1, "guisado": "Guisado Inventado"}],
        turno="TARDE",
    )
    assert "guisado válido" in respuesta.get_data(as_text=True)


def test_taco_con_guisado_descuenta_guisado_correcto(mesero_logueado, app):
    client = mesero_logueado
    with app.app_context():
        stock_barbacoa_antes = stock_insumo("INS-GUI-BAR")
        taco_id = producto_id("TAR-TACOS")

    respuesta = _confirmar(
        client,
        [{"producto_id": taco_id, "cantidad": 1, "guisado": "Barbacoa"}],
        turno="TARDE",
    )
    assert "registrada" in respuesta.get_data(as_text=True)

    with app.app_context():
        assert round(stock_insumo("INS-GUI-BAR"), 4) == round(
            stock_barbacoa_antes - 0.12, 4
        )


def test_turno_incompatible_es_rechazado(mesero_logueado, app):
    client = mesero_logueado
    with app.app_context():
        pozole_id = producto_id("TAR-POZOLE")

    respuesta = _confirmar(client, [{"producto_id": pozole_id, "cantidad": 1}], turno="MANANA")
    assert "no pertenece al turno" in respuesta.get_data(as_text=True)


def test_ticket_muestra_logo_y_totales(mesero_logueado, app):
    client = mesero_logueado
    with app.app_context():
        latte_id = producto_id("BEB-LATTE")

    respuesta = _confirmar(client, [{"producto_id": latte_id, "cantidad": 1}])
    texto = respuesta.get_data(as_text=True)
    assert "La Época de Oro" in texto
    assert "Café, Guisados y Nostalgia" in texto
    assert "$45.00" in texto


def test_comanda_solo_la_ve_y_procesa_chef(mesero_logueado, app):
    client = mesero_logueado
    with app.app_context():
        cafe_id = producto_id("BEB-CAF-AM")

    _confirmar(client, [{"producto_id": cafe_id, "cantidad": 1}])

    respuesta = client.get("/cocina/")
    assert respuesta.status_code == 403

    with app.app_context():
        comanda = Comanda.query.order_by(Comanda.id.desc()).first()
        comanda_id = comanda.id

    iniciar_sesion(client, "chef1", "chef123")
    respuesta = client.get("/cocina/")
    assert respuesta.status_code == 200
    assert "En preparación" in respuesta.get_data(as_text=True)

    respuesta = client.post(f"/cocina/comanda/{comanda_id}/listo", follow_redirects=True)
    assert "lista para entregar" in respuesta.get_data(as_text=True)

    with app.app_context():
        comanda = db.session.get(Comanda, comanda_id)
        assert comanda.estado == "LISTA"

    client.post(f"/cocina/comanda/{comanda_id}/entregar", follow_redirects=True)
    with app.app_context():
        comanda = db.session.get(Comanda, comanda_id)
        assert comanda.estado == "ENTREGADA"
