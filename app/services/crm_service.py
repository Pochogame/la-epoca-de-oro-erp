from datetime import datetime

from app.extensions import db
from app.models.crm import Cliente
from app.models.ventas import Venta
from app.repositories.crm_repository import ClienteRepositorio
from app.services.excepciones import DatosInvalidosError


def _normalizar_telefono(telefono):
    digitos = "".join(caracter for caracter in (telefono or "") if caracter.isdigit())
    if len(digitos) < 7:
        raise DatosInvalidosError("El teléfono debe tener al menos 7 dígitos.")
    return digitos


def _parsear_fecha(valor):
    valor = (valor or "").strip()
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        raise DatosInvalidosError("La fecha de cumpleaños no es válida.") from None


class ClienteService:
    def __init__(self, clientes=None):
        self.clientes = clientes or ClienteRepositorio()

    def listar(self, busqueda=None):
        return self.clientes.buscar(busqueda)

    def activos(self):
        return self.clientes.activos()

    def obtener(self, cliente_id):
        return self.clientes.obtener(cliente_id)

    def crear(self, nombre, telefono, email="", cumpleanos="", notas=""):
        nombre = (nombre or "").strip()
        if not nombre:
            raise DatosInvalidosError("El nombre del cliente es obligatorio.")
        telefono = _normalizar_telefono(telefono)
        if self.clientes.por_telefono(telefono) is not None:
            raise DatosInvalidosError("Ya existe un cliente con ese teléfono.")
        cliente = Cliente(
            nombre=nombre,
            telefono=telefono,
            email=(email or "").strip(),
            cumpleanos=_parsear_fecha(cumpleanos),
            notas=(notas or "").strip(),
        )
        self.clientes.agregar(cliente)
        db.session.commit()
        return cliente

    def actualizar(self, cliente_id, nombre, telefono, email="", cumpleanos="", notas="", activo=True):
        cliente = self.clientes.obtener(cliente_id)
        if cliente is None:
            raise DatosInvalidosError("El cliente indicado no existe.")
        nombre = (nombre or "").strip()
        if not nombre:
            raise DatosInvalidosError("El nombre del cliente es obligatorio.")
        telefono = _normalizar_telefono(telefono)
        existente = self.clientes.por_telefono(telefono)
        if existente is not None and existente.id != cliente.id:
            raise DatosInvalidosError("Ya existe otro cliente con ese teléfono.")

        cliente.nombre = nombre
        cliente.telefono = telefono
        cliente.email = (email or "").strip()
        cliente.cumpleanos = _parsear_fecha(cumpleanos)
        cliente.notas = (notas or "").strip()
        cliente.activo = bool(activo)
        db.session.commit()
        return cliente

    def metricas(self, cliente_id):
        cliente = self.clientes.obtener(cliente_id)
        if cliente is None:
            return None
        ventas = (
            Venta.query.filter(
                Venta.cliente_id == cliente.id,
                Venta.cancelada.is_(False),
                Venta.cobrada_en.isnot(None),
            )
            .order_by(Venta.cobrada_en.desc())
            .all()
        )
        total = round(sum(venta.total for venta in ventas), 2)
        visitas = len(
            {
                f"cuenta-{venta.cuenta_id}" if venta.cuenta_id else f"venta-{venta.id}"
                for venta in ventas
            }
        )
        return {
            "cliente": cliente,
            "ventas": ventas,
            "total": total,
            "visitas": visitas,
            "ticket_promedio": round(total / visitas, 2) if visitas else 0.0,
            "ultima_compra": ventas[0].cobrada_en if ventas else None,
        }
