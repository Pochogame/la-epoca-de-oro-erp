import pytest

from app import create_app


@pytest.fixture()
def app():
    aplicacion = create_app("testing")
    yield aplicacion


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def contexto(app):
    with app.app_context():
        yield


def iniciar_sesion(client, username, password, seguir=True):
    client.post("/logout")
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=seguir,
    )


@pytest.fixture()
def mesero_logueado(client):
    iniciar_sesion(client, "mesero1", "mesero123")
    return client


@pytest.fixture()
def chef_logueado(client):
    iniciar_sesion(client, "chef1", "chef123")
    return client


@pytest.fixture()
def admin_logueado(client):
    iniciar_sesion(client, "admin", "admin123")
    return client


def producto_id(codigo):
    from app.models.menu import Producto

    return Producto.query.filter_by(codigo=codigo).first().id


def insumo_id(codigo):
    from app.models.inventario import Insumo

    return Insumo.query.filter_by(codigo=codigo).first().id


def usuario_id(username):
    from app.models.usuario import Usuario

    return Usuario.query.filter_by(username=username).first().id


def stock_insumo(insumo_codigo, almacen_codigo="ALM-MP"):
    from app.models.inventario import Almacen, Insumo, StockAlmacen

    insumo = Insumo.query.filter_by(codigo=insumo_codigo).first()
    almacen = Almacen.query.filter_by(codigo=almacen_codigo).first()
    if almacen is None:
        almacen = Almacen.query.order_by(Almacen.id).first()
    registro = StockAlmacen.query.filter_by(insumo_id=insumo.id, almacen_id=almacen.id).first()
    return registro.cantidad if registro else 0.0
