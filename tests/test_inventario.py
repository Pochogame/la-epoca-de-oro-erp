from app.extensions import db
from app.models.contabilidad import Asiento
from app.models.inventario import Merma, MovimientoInventario
from tests.conftest import iniciar_sesion, insumo_id, stock_insumo


def test_entrada_aumenta_stock_y_genera_asiento(chef_logueado, app):
    client = chef_logueado
    with app.app_context():
        id_cafe = insumo_id("INS-CAF")
        id_mp = 1
        stock_antes = stock_insumo("INS-CAF", "ALM-MP")
        asientos_antes = Asiento.query.filter_by(origen="COMPRA").count()

    respuesta = client.post(
        "/inventario/entrada",
        data={
            "insumo_id": id_cafe,
            "cantidad": "5",
            "costo_unitario": "280",
            "almacen_destino_id": id_mp,
            "estado_pago": "PAGADO",
            "referencia": "Proveedor de prueba",
        },
        follow_redirects=True,
    )
    assert "registrada correctamente" in respuesta.get_data(as_text=True)

    with app.app_context():
        assert round(stock_insumo("INS-CAF", "ALM-MP"), 2) == round(stock_antes + 5, 2)
        assert Asiento.query.filter_by(origen="COMPRA").count() == asientos_antes + 1


def test_entrada_pendiente_aparece_en_cuentas_por_pagar(chef_logueado, admin_logueado, app):
    client = chef_logueado
    with app.app_context():
        id_leche = insumo_id("INS-LEC")

    client.post(
        "/inventario/entrada",
        data={
            "insumo_id": id_leche,
            "cantidad": "10",
            "costo_unitario": "26",
            "almacen_destino_id": 1,
            "estado_pago": "PENDIENTE",
            "referencia": "Compra a crédito",
        },
        follow_redirects=True,
    )

    iniciar_sesion(client, "admin", "admin123")
    respuesta = client.get("/contabilidad/flujo-caja")
    assert "Compra a crédito" in respuesta.get_data(as_text=True)

    with app.app_context():
        movimiento = (
            MovimientoInventario.query.filter_by(estado_pago="PENDIENTE", tipo="ENTRADA")
            .order_by(MovimientoInventario.id.desc())
            .first()
        )
        movimiento_id = movimiento.id

    respuesta = client.post(f"/contabilidad/compras/{movimiento_id}/pagar", follow_redirects=True)
    assert "marcada como pagada" in respuesta.get_data(as_text=True)

    with app.app_context():
        movimiento = db.session.get(MovimientoInventario, movimiento_id)
        assert movimiento.estado_pago == "PAGADO"


def test_transferencia_mueve_stock_entre_almacenes(chef_logueado, app):
    client = chef_logueado
    with app.app_context():
        id_pollo = insumo_id("INS-POL")
        origen = stock_insumo("INS-POL", "ALM-MP")
        destino = stock_insumo("INS-POL", "ALM-COC")

    respuesta = client.post(
        "/inventario/transferencia",
        data={
            "insumo_id": id_pollo,
            "almacen_origen_id": 1,
            "almacen_destino_id": 2,
            "cantidad": "3",
        },
        follow_redirects=True,
    )
    assert "realizada" in respuesta.get_data(as_text=True)

    with app.app_context():
        assert round(stock_insumo("INS-POL", "ALM-MP"), 2) == round(origen - 3, 2)
        assert round(stock_insumo("INS-POL", "ALM-COC"), 2) == round(destino + 3, 2)


def test_transferencia_sin_stock_es_rechazada(chef_logueado, app):
    client = chef_logueado
    with app.app_context():
        id_oreo = insumo_id("INS-ORE")

    respuesta = client.post(
        "/inventario/transferencia",
        data={
            "insumo_id": id_oreo,
            "almacen_origen_id": 1,
            "almacen_destino_id": 2,
            "cantidad": "99999",
        },
        follow_redirects=True,
    )
    assert "Stock insuficiente" in respuesta.get_data(as_text=True)


def test_merma_descuenta_stock_y_registra_motivo(chef_logueado, app):
    client = chef_logueado
    with app.app_context():
        id_fresa = insumo_id("INS-FRE")
        stock_antes = stock_insumo("INS-FRE", "ALM-COC")

    respuesta = client.post(
        "/inventario/merma",
        data={
            "insumo_id": id_fresa,
            "almacen_id": 2,
            "cantidad": "0.5",
            "motivo": "Alimento caducado",
            "comentario": "Fresa pasada del fin de semana",
        },
        follow_redirects=True,
    )
    assert "Merma registrada" in respuesta.get_data(as_text=True)

    with app.app_context():
        assert round(stock_insumo("INS-FRE", "ALM-COC"), 2) == round(stock_antes - 0.5, 2)
        merma = Merma.query.order_by(Merma.id.desc()).first()
        assert merma.motivo == "Alimento caducado"
        assert merma.costo_estimado == 45.0


def test_motivo_de_merma_invalido_es_rechazado(chef_logueado, app):
    client = chef_logueado
    with app.app_context():
        id_fresa = insumo_id("INS-FRE")

    respuesta = client.post(
        "/inventario/merma",
        data={
            "insumo_id": id_fresa,
            "almacen_id": 2,
            "cantidad": "1",
            "motivo": "Motivo inexistente",
        },
        follow_redirects=True,
    )
    assert "motivo de la merma no es válido" in respuesta.get_data(as_text=True)


def test_alerta_de_stock_minimo_se_muestra(chef_logueado, app):
    client = chef_logueado
    with app.app_context():
        from app.models.inventario import Insumo

        oreo = Insumo.query.filter_by(codigo="INS-ORE").first()
        for stock in oreo.stocks:
            stock.cantidad = 0.0
        db.session.commit()

    respuesta = client.get("/inventario/")
    assert "stock mínimo" in respuesta.get_data(as_text=True)
    assert "Galleta Oreo" in respuesta.get_data(as_text=True)


def test_mesero_no_accede_a_inventario(mesero_logueado):
    respuesta = mesero_logueado.get("/inventario/")
    assert respuesta.status_code == 403


def test_crear_insumo_nuevo(chef_logueado, app):
    client = chef_logueado
    respuesta = client.post(
        "/inventario/insumos",
        data={
            "codigo": "INS-PIM",
            "nombre": "Pimiento morrón",
            "unidad": "kg",
            "costo_unitario": "75",
            "stock_minimo": "1",
        },
        follow_redirects=True,
    )
    assert "registrado en el catálogo" in respuesta.get_data(as_text=True)

    respuesta = client.post(
        "/inventario/insumos",
        data={
            "codigo": "INS-PIM",
            "nombre": "Duplicado",
            "unidad": "kg",
            "costo_unitario": "75",
            "stock_minimo": "1",
        },
        follow_redirects=True,
    )
    assert "Ya existe un insumo" in respuesta.get_data(as_text=True)
