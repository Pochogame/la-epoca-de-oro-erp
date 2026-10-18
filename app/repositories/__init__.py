from app.repositories.contabilidad_repository import (
    AsientoRepositorio,
    CuentaContableRepositorio,
    GastoRepositorio,
)
from app.repositories.inventario_repository import (
    AlmacenRepositorio,
    InsumoRepositorio,
    MermaRepositorio,
    MovimientoRepositorio,
)
from app.repositories.menu_repository import ProductoRepositorio
from app.repositories.rrhh_repository import AsistenciaRepositorio, NominaRepositorio
from app.repositories.usuario_repository import UsuarioRepositorio
from app.repositories.venta_repository import ComandaRepositorio, VentaRepositorio

__all__ = [
    "AlmacenRepositorio",
    "AsientoRepositorio",
    "AsistenciaRepositorio",
    "ComandaRepositorio",
    "CuentaContableRepositorio",
    "GastoRepositorio",
    "InsumoRepositorio",
    "MermaRepositorio",
    "MovimientoRepositorio",
    "NominaRepositorio",
    "ProductoRepositorio",
    "UsuarioRepositorio",
    "VentaRepositorio",
]
