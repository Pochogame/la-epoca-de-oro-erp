import json
from datetime import datetime

from app.constants import EstadoComanda
from app.extensions import db
from app.models.crm import Cliente
from app.models.menu import Producto, ProductoVariante
from app.models.ventas import Mesa, Venta
from app.services.crm_service import ClienteService
from app.services.excepciones import DatosInvalidosError
from app.services.venta_service import VentaService
from tests.conftest import producto_id, stock_insumo, usuario_id


def _confirmar(client, items, turno="TARDE", tipo="AQUI", metodo="EFECTIVO", **extra):
    datos = {
        "turno": turno,
        "tipo_orden": tipo,
        "metodo_pago": metodo,
        "items_json": json.dumps(items),
    }
    datos.update(extra)
    return client.post("/pos/confirmar", data=datos, follow_redirects=True)


def test_pos_pide_tamano_y_muestra_precio_desde(mesero_logueado):
    texto = mesero_logueado.get("/pos/?turno=TARDE").get_data(as_text=True)
    assert "Pozole Rojo o Verde" in texto
    assert "desde" in texto
    assert "Chico" in texto
    assert "Medio" in texto
    assert "Litro" in texto


def test_pozole_grande_usa_precio_y_factor_de_receta(mesero_logueado, app):
    with app.app_context():
        stock_maiz_antes = stock_insumo("INS-MAI")
        pozole_id = producto_id("TAR-POZOLE")

    respuesta = _confirmar(
        mesero_logueado,
        [
            {
                "producto_id": pozole_id,
                "cantidad": 1,
                "variante_nombre": "Grande",
            }
        ],
    )
    assert "registrada" in respuesta.get_data(as_text=True)

    with app.app_context():
        venta = Venta.query.order_by(Venta.id.desc()).first()
        assert venta.total == 110.0
        detalle = venta.detalles[0]
        assert detalle.variante_nombre == "Grande"
        assert round(stock_insumo("INS-MAI"), 4) == round(stock_maiz_antes - 0.26, 4)


def test_producto_con_tamanos_requiere_seleccion(mesero_logueado, app):
    with app.app_context():
        pozole_id = producto_id("TAR-POZOLE")

    respuesta = _confirmar(
        mesero_logueado, [{"producto_id": pozole_id, "cantidad": 1}]
    )
    assert "Selecciona un tamaño válido" in respuesta.get_data(as_text=True)


def test_taco_individual_cuesta_trece(mesero_logueado, app):
    with app.app_context():
        taco_id = producto_id("TAR-TACOS")

    respuesta = _confirmar(
        mesero_logueado,
        [{"producto_id": taco_id, "cantidad": 3, "guisado": "Barbacoa"}],
    )
    assert "registrada" in respuesta.get_data(as_text=True)

    with app.app_context():
        venta = Venta.query.order_by(Venta.id.desc()).first()
        assert venta.total == 39.0


def test_disponibilidad_marca_solo_lo_que_falta(mesero_logueado, app):
    with app.app_context():
        concha = Producto.query.filter_by(codigo="PAN-CONCHA").first()
        for stock in concha.receta[0].insumo.stocks:
            stock.cantidad = 0.0
        db.session.commit()
        cafe_id = producto_id("BEB-CAF-AM")
        concha_id = producto_id("PAN-CONCHA")

    respuesta = mesero_logueado.post(
        "/pos/disponibilidad",
        json={
            "turno": "MANANA",
            "items": [
                {"producto_id": cafe_id, "cantidad": 1},
                {"producto_id": concha_id, "cantidad": 1},
            ],
        },
    )
    datos = respuesta.get_json()
    assert datos["no_disponibles"] == 1
    assert datos["lineas"][0]["disponible"] is True
    assert datos["lineas"][1]["disponible"] is False
    assert "Concha" in datos["lineas"][1]["motivo"]


def test_crm_crear_cliente_y_ver_historial(admin_logueado, app):
    respuesta = admin_logueado.post(
        "/crm/nuevo",
        data={
            "nombre": "Laura Méndez",
            "telefono": "477-123-9988",
            "email": "laura@example.com",
            "cumpleanos": "1992-03-18",
            "notas": "Cliente de comida corrida.",
        },
        follow_redirects=True,
    )
    assert "Cliente registrado" in respuesta.get_data(as_text=True)

    with app.app_context():
        cliente = Cliente.query.filter_by(telefono="4771239988").first()
        assert cliente is not None
        cliente_id = cliente.id
        cafe_id = producto_id("BEB-CAF-AM")
        mesero_id = usuario_id("mesero1")
        VentaService().registrar_venta(
            mesero_id=mesero_id,
            turno="MANANA",
            tipo_orden="LLEVAR",
            metodo_pago="EFECTIVO",
            items=[{"producto_id": cafe_id, "cantidad": 1}],
            usuario_id=mesero_id,
            cliente_id=cliente_id,
        )

    texto = admin_logueado.get(f"/crm/{cliente_id}").get_data(as_text=True)
    assert "Laura Méndez" in texto
    assert "Historial de compras" in texto
    assert "$35.00" in texto
    assert "Café Americano" in texto

    texto_lista = admin_logueado.get("/crm/?q=9988").get_data(as_text=True)
    assert "Laura Méndez" in texto_lista
    texto_lista = admin_logueado.get("/crm/?q=477-123-9988").get_data(as_text=True)
    assert "Laura Méndez" in texto_lista


def test_crm_telefono_duplicado_es_rechazado(admin_logueado, app):
    with app.app_context():
        cliente = ClienteService().crear("Cliente Uno", "4770001111")

    respuesta = admin_logueado.post(
        "/crm/nuevo",
        data={"nombre": "Cliente Dos", "telefono": "477 000 1111"},
        follow_redirects=True,
    )
    assert "Ya existe un cliente con ese teléfono" in respuesta.get_data(as_text=True)

    with app.app_context():
        assert Cliente.query.filter_by(telefono="4770001111").count() == 1


def test_mesero_no_accede_al_crm(mesero_logueado):
    assert mesero_logueado.get("/crm/").status_code == 403


def test_cuenta_hereda_cliente_a_todas_las_rondas(app):
    with app.app_context():
        cliente = ClienteService().crear("Cliente Mesa", "4772223333")
        mesa = Mesa.query.filter_by(estado="LIBRE").first()
        cafe_id = producto_id("BEB-CAF-AM")
        pan_id = producto_id("PAN-CONCHA")
        mesero_id = usuario_id("mesero1")
        ventas = VentaService()

        primera = ventas.registrar_venta(
            mesero_id=mesero_id,
            turno="MANANA",
            tipo_orden="AQUI",
            metodo_pago="EFECTIVO",
            items=[{"producto_id": cafe_id, "cantidad": 1}],
            usuario_id=mesero_id,
            mesa_id=mesa.id,
            cliente_id=cliente.id,
        )
        segunda = ventas.registrar_venta(
            mesero_id=mesero_id,
            turno="MANANA",
            tipo_orden="AQUI",
            metodo_pago="EFECTIVO",
            items=[{"producto_id": pan_id, "cantidad": 1}],
            usuario_id=mesero_id,
            mesa_id=mesa.id,
        )
        cuenta = primera.cuenta
        assert cuenta.cliente_id == cliente.id
        assert segunda.cliente_id == cliente.id
        assert segunda.comanda.ronda == 2

        for venta in cuenta.ventas:
            venta.comanda.estado = EstadoComanda.ENTREGADA
            venta.comanda.cerrada_en = datetime.now()
        ventas.cobrar_cuenta(cuenta.id, "EFECTIVO", usuario_id=mesero_id)
        assert all(venta.cliente_id == cliente.id for venta in cuenta.ventas)


def test_cuenta_no_cambia_de_cliente_desde_una_ronda(app):
    with app.app_context():
        clientes = ClienteService()
        cliente_uno = clientes.crear("Cliente Uno", "4771112222")
        cliente_dos = clientes.crear("Cliente Dos", "4773334444")
        mesa = Mesa.query.filter_by(estado="LIBRE").first()
        cafe_id = producto_id("BEB-CAF-AM")
        mesero_id = usuario_id("mesero1")
        ventas = VentaService()

        ventas.registrar_venta(
            mesero_id=mesero_id,
            turno="MANANA",
            tipo_orden="AQUI",
            metodo_pago="EFECTIVO",
            items=[{"producto_id": cafe_id, "cantidad": 1}],
            usuario_id=mesero_id,
            mesa_id=mesa.id,
            cliente_id=cliente_uno.id,
        )

        try:
            ventas.registrar_venta(
                mesero_id=mesero_id,
                turno="MANANA",
                tipo_orden="AQUI",
                metodo_pago="EFECTIVO",
                items=[{"producto_id": cafe_id, "cantidad": 1}],
                usuario_id=mesero_id,
                mesa_id=mesa.id,
                cliente_id=cliente_dos.id,
            )
        except DatosInvalidosError as error:
            assert "otro cliente" in error.mensaje
        else:
            raise AssertionError("La cuenta permitió cambiar de cliente desde una ronda")


def test_editar_producto_y_crear_tamano(chef_logueado, app):
    with app.app_context():
        producto = Producto.query.filter_by(codigo="TAR-AGU-PEP").first()
        producto_id_actual = producto.id

    respuesta = chef_logueado.post(
        f"/recetas/producto/{producto_id_actual}/editar",
        data={
            "codigo": "TAR-AGU-PEP",
            "nombre": "Agua de Pepino",
            "categoria": "Aguas Frescas",
            "precio": "36",
            "turno": "TARDE",
            "activo": "on",
        },
        follow_redirects=True,
    )
    assert "Producto actualizado" in respuesta.get_data(as_text=True)

    respuesta = chef_logueado.post(
        f"/recetas/producto/{producto_id_actual}/variante",
        data={"nombre": "Jarra", "precio": "60", "factor_receta": "2.0"},
        follow_redirects=True,
    )
    assert "Tamaño agregado" in respuesta.get_data(as_text=True)

    with app.app_context():
        producto = db.session.get(Producto, producto_id_actual)
        assert producto.nombre == "Agua de Pepino"
        assert producto.precio == 36.0
        variante = ProductoVariante.query.filter_by(
            producto_id=producto.id, nombre="Jarra"
        ).first()
        assert variante is not None
        assert variante.precio == 60.0
        assert variante.factor_receta == 2.0


def test_migracion_consolida_stock_en_almacen_principal(app):
    with app.app_context():
        from app.migraciones import _consolidar_almacen_principal
        from app.models.inventario import Almacen, StockAlmacen

        principal = Almacen.query.filter_by(codigo="ALM-MP").first()
        cocina = Almacen(codigo="ALM-COC", nombre="Cocina")
        pos = Almacen(codigo="ALM-POS", nombre="POS")
        db.session.add_all([cocina, pos])
        db.session.flush()

        producto = Producto.query.filter_by(codigo="TAR-POZOLE").first()
        producto.almacen_consumo_id = cocina.id
        insumo = producto.receta[0].insumo
        stock_mp = StockAlmacen.query.filter_by(
            insumo_id=insumo.id, almacen_id=principal.id
        ).first()
        stock_mp.cantidad = 5.0
        db.session.add_all(
            [
                StockAlmacen(insumo_id=insumo.id, almacen_id=cocina.id, cantidad=3.0),
                StockAlmacen(insumo_id=insumo.id, almacen_id=pos.id, cantidad=2.0),
            ]
        )
        db.session.commit()

        _consolidar_almacen_principal()

        assert round(stock_mp.cantidad, 4) == 10.0
        assert all(
            stock.cantidad == 0
            for stock in StockAlmacen.query.filter(
                StockAlmacen.almacen_id != principal.id
            )
        )
        assert producto.almacen_consumo_id == principal.id
