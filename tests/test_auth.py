from app.models.usuario import Usuario
from tests.conftest import iniciar_sesion


def test_login_admin_correcto(client):
    respuesta = iniciar_sesion(client, "admin", "admin123")
    assert respuesta.status_code == 200
    assert "Panel General" in respuesta.get_data(as_text=True)


def test_login_password_incorrecta(client):
    respuesta = iniciar_sesion(client, "admin", "clave-mala")
    assert "incorrectos" in respuesta.get_data(as_text=True)


def test_login_usuario_inexistente(client):
    respuesta = iniciar_sesion(client, "fantasma", "cualquiera")
    assert "incorrectos" in respuesta.get_data(as_text=True)


def test_mesero_es_redirigido_al_pos(client):
    iniciar_sesion(client, "mesero1", "mesero123")
    respuesta = client.get("/", follow_redirects=True)
    assert "Toma de pedidos" in respuesta.get_data(as_text=True)


def test_chef_es_redirigido_a_cocina(client):
    iniciar_sesion(client, "chef1", "chef123")
    respuesta = client.get("/", follow_redirects=True)
    assert "Pantalla de cocina" in respuesta.get_data(as_text=True)


def test_mesero_no_puede_entrar_a_contabilidad(client):
    iniciar_sesion(client, "mesero1", "mesero123")
    respuesta = client.get("/contabilidad/estado-resultados")
    assert respuesta.status_code == 403


def test_mesero_no_puede_entrar_a_usuarios(client):
    iniciar_sesion(client, "mesero1", "mesero123")
    respuesta = client.get("/admin/usuarios")
    assert respuesta.status_code == 403


def test_chef_no_puede_entrar_a_admin(client):
    iniciar_sesion(client, "chef1", "chef123")
    respuesta = client.get("/admin/usuarios")
    assert respuesta.status_code == 403


def test_chef_puede_entrar_a_inventario(client):
    iniciar_sesion(client, "chef1", "chef123")
    respuesta = client.get("/inventario/")
    assert respuesta.status_code == 200
    assert "Inventario" in respuesta.get_data(as_text=True)


def test_admin_puede_entrar_a_todo(client):
    iniciar_sesion(client, "admin", "admin123")
    for ruta in (
        "/pos/",
        "/cocina/",
        "/inventario/",
        "/recetas/",
        "/contabilidad/estado-resultados",
        "/contabilidad/libro-diario",
        "/contabilidad/gastos",
        "/contabilidad/flujo-caja",
        "/rrhh/asistencias",
        "/rrhh/nomina",
        "/admin/usuarios",
    ):
        respuesta = client.get(ruta)
        assert respuesta.status_code == 200, f"Ruta con error: {ruta}"


def test_sin_sesion_redirige_a_login(client):
    respuesta = client.get("/inventario/")
    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]


def test_logout(client):
    iniciar_sesion(client, "admin", "admin123")
    respuesta = client.post("/logout", follow_redirects=True)
    assert "Acceso al sistema" in respuesta.get_data(as_text=True)


def test_restablecer_password(client, app):
    respuesta = client.post(
        "/recuperar-password",
        data={"username": "chef1", "email": "chef1@laepocadeoro.com", "password": "nueva-clave-1"},
        follow_redirects=True,
    )
    assert "actualizada" in respuesta.get_data(as_text=True)

    assert iniciar_sesion(client, "chef1", "nueva-clave-1", seguir=False).status_code == 302

    with app.app_context():
        chef = Usuario.query.filter_by(username="chef1").first()
        assert chef.verificar_password("nueva-clave-1")
        assert not chef.verificar_password("chef123")


def test_restablecer_password_correo_incorrecto(client):
    respuesta = client.post(
        "/recuperar-password",
        data={"username": "chef1", "email": "otro@correo.com", "password": "nueva-clave-1"},
        follow_redirects=True,
    )
    assert "no coinciden" in respuesta.get_data(as_text=True)


def test_password_se_guarda_cifrada(app):
    with app.app_context():
        admin = Usuario.query.filter_by(username="admin").first()
        assert admin.password_hash != "admin123"
        assert admin.verificar_password("admin123")
        assert admin.fecha_alta is not None
