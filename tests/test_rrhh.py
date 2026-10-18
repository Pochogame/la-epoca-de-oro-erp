from datetime import date

from app.models.contabilidad import GastoOperativo
from app.models.rrhh import Asistencia, NominaPago
from app.services.excepciones import OperacionDuplicadaError
from app.services.rrhh_service import RRHHService
from tests.conftest import usuario_id


def test_registrar_asistencia_por_http(admin_logueado, app):
    with app.app_context():
        id_mesero2 = usuario_id("mesero2")

    respuesta = admin_logueado.post(
        "/rrhh/asistencias",
        data={
            "usuario_id": id_mesero2,
            "fecha": "2026-01-05",
            "hora_entrada": "08:00",
            "hora_salida": "16:30",
            "estado": "PRESENTE",
        },
        follow_redirects=True,
    )
    assert "Asistencia registrada" in respuesta.get_data(as_text=True)

    with app.app_context():
        asistencia = Asistencia.query.filter_by(
            usuario_id=id_mesero2, fecha=date(2026, 1, 5)
        ).first()
        assert asistencia is not None
        assert asistencia.estado == "PRESENTE"
        assert asistencia.horas_trabajadas == 8.5


def test_asistencia_duplicada_se_actualiza(admin_logueado, app):
    with app.app_context():
        id_mesero2 = usuario_id("mesero2")

    datos = {
        "usuario_id": id_mesero2,
        "fecha": "2026-01-06",
        "hora_entrada": "08:00",
        "hora_salida": "16:00",
        "estado": "PRESENTE",
    }
    admin_logueado.post("/rrhh/asistencias", data=datos, follow_redirects=True)
    datos["estado"] = "RETARDO"
    admin_logueado.post("/rrhh/asistencias", data=datos, follow_redirects=True)

    with app.app_context():
        registros = Asistencia.query.filter_by(
            usuario_id=id_mesero2, fecha=date(2026, 1, 6)
        ).all()
        assert len(registros) == 1
        assert registros[0].estado == "RETARDO"


def test_fecha_futura_es_rechazada(admin_logueado, app):
    with app.app_context():
        id_mesero2 = usuario_id("mesero2")

    respuesta = admin_logueado.post(
        "/rrhh/asistencias",
        data={
            "usuario_id": id_mesero2,
            "fecha": "2099-01-01",
            "estado": "PRESENTE",
        },
        follow_redirects=True,
    )
    assert "fechas futuras" in respuesta.get_data(as_text=True)


def test_calculo_de_nomina(app):
    with app.app_context():
        id_mesero2 = usuario_id("mesero2")
        servicio = RRHHService()
        servicio.registrar_asistencia(id_mesero2, date(2026, 2, 2), None, None, "PRESENTE")
        servicio.registrar_asistencia(id_mesero2, date(2026, 2, 3), None, None, "RETARDO")
        servicio.registrar_asistencia(id_mesero2, date(2026, 2, 4), None, None, "FALTA")

        calculo = servicio.calcular_nomina(date(2026, 2, 2), date(2026, 2, 4))
        fila = next(f for f in calculo["filas"] if f["usuario"].id == id_mesero2)
        assert fila["dias_trabajados"] == 2
        assert fila["faltas"] == 1
        assert fila["total"] == 700.0
        assert calculo["total"] == 700.0


def test_pago_de_nomina_genera_gasto_y_no_se_duplica(app):
    with app.app_context():
        id_mesero2 = usuario_id("mesero2")
        servicio = RRHHService()
        servicio.registrar_asistencia(id_mesero2, date(2026, 3, 2), None, None, "PRESENTE")

        nomina = servicio.registrar_pago(date(2026, 3, 1), date(2026, 3, 7))
        assert nomina.total == 350.0

        gasto = (
            GastoOperativo.query.filter_by(categoria="NOMINA")
            .order_by(GastoOperativo.id.desc())
            .first()
        )
        assert gasto.monto == 350.0
        assert gasto.estado == "PAGADO"

        registro = NominaPago.query.filter_by(desde=date(2026, 3, 1)).first()
        assert registro is not None

        try:
            servicio.registrar_pago(date(2026, 3, 1), date(2026, 3, 7))
            assert False, "Debió lanzar OperacionDuplicadaError"
        except OperacionDuplicadaError:
            pass


def test_nomina_sin_asistencias_no_se_puede_pagar(app):
    with app.app_context():
        servicio = RRHHService()
        try:
            servicio.registrar_pago(date(2029, 1, 1), date(2029, 1, 7))
            assert False, "Debió lanzar un error de negocio"
        except Exception as error:
            assert "días trabajados" in str(error).lower() or "asistencias" in str(error).lower()


def test_mesero_no_accede_a_rrhh(mesero_logueado):
    assert mesero_logueado.get("/rrhh/asistencias").status_code == 403
    assert mesero_logueado.get("/rrhh/nomina").status_code == 403
