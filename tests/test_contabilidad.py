from app.models.contabilidad import Asiento, GastoOperativo
from tests.conftest import iniciar_sesion


def test_estado_resultados_refleja_ventas_reales(admin_logueado):
    respuesta = admin_logueado.get("/contabilidad/estado-resultados")
    texto = respuesta.get_data(as_text=True)
    assert "UTILIDAD NETA OPERATIVA DEL PERIODO" in texto
    assert "$415.00" in texto
    assert "UTILIDAD BRUTA" in texto


def test_libro_diario_cuadrado(admin_logueado):
    respuesta = admin_logueado.get("/contabilidad/libro-diario")
    texto = respuesta.get_data(as_text=True)
    assert "Periodo cuadrado" in texto
    assert "Venta VTA-" in texto


def test_registrar_gasto_genera_asiento_y_cxp(admin_logueado, app):
    client = admin_logueado
    with app.app_context():
        asientos_antes = Asiento.query.filter_by(origen="GASTO").count()

    respuesta = client.post(
        "/contabilidad/gastos",
        data={
            "categoria": "AGUA",
            "descripcion": "Recibo de agua del mes",
            "monto": "420.50",
            "estado": "PENDIENTE",
        },
        follow_redirects=True,
    )
    assert "asiento contable generado" in respuesta.get_data(as_text=True)

    with app.app_context():
        assert Asiento.query.filter_by(origen="GASTO").count() == asientos_antes + 1
        gasto = (
            GastoOperativo.query.filter_by(descripcion="Recibo de agua del mes")
            .order_by(GastoOperativo.id.desc())
            .first()
        )
        assert gasto.estado == "PENDIENTE"
        gasto_id = gasto.id

    respuesta = client.get("/contabilidad/flujo-caja")
    texto = respuesta.get_data(as_text=True)
    assert "Recibo de agua del mes" in texto
    assert "$420.50" in texto

    respuesta = client.post(
        f"/contabilidad/gastos/{gasto_id}/pagar", follow_redirects=True
    )
    assert "marcado como pagado" in respuesta.get_data(as_text=True)

    with app.app_context():
        gasto = GastoOperativo.query.filter_by(id=gasto_id).first()
        assert gasto.estado == "PAGADO"
        assert gasto.fecha_pago is not None


def test_gasto_con_monto_invalido_es_rechazado(admin_logueado):
    respuesta = admin_logueado.post(
        "/contabilidad/gastos",
        data={
            "categoria": "GAS",
            "descripcion": "Prueba",
            "monto": "-50",
            "estado": "PAGADO",
        },
        follow_redirects=True,
    )
    assert "mayor a cero" in respuesta.get_data(as_text=True)


def test_categoria_de_gasto_invalida_es_rechazada(admin_logueado):
    respuesta = admin_logueado.post(
        "/contabilidad/gastos",
        data={
            "categoria": "LUJOS",
            "descripcion": "Prueba",
            "monto": "100",
            "estado": "PAGADO",
        },
        follow_redirects=True,
    )
    assert "no es válida" in respuesta.get_data(as_text=True)


def test_cuentas_por_pagar_incluye_renta_sembrada(admin_logueado):
    respuesta = admin_logueado.get("/contabilidad/flujo-caja")
    texto = respuesta.get_data(as_text=True)
    assert "Renta del local" in texto
    assert "Gastos pendientes de pago" in texto


def test_mesero_no_ve_libro_diario(mesero_logueado):
    respuesta = mesero_logueado.get("/contabilidad/libro-diario")
    assert respuesta.status_code == 403
