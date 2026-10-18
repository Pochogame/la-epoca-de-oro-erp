# La Época de Oro ERP

Sistema ERP + POS para "La Época de Oro (Café, Guisados y Nostalgia)": punto de venta por turnos, comandas a cocina, inventario multi-almacén con recetas (BOM), contabilidad de partida doble, RRHH con nómina y control de acceso por roles.

## Stack

- Python 3.10+ con Flask 3, Flask-SQLAlchemy y SQLite (sin servicios externos).
- Jinja2 + Tailwind CSS (CDN) + JavaScript vanilla para el carrito del POS y gráficas (Chart.js CDN por página).
- pytest para las pruebas (58 pruebas de integración con base de datos en memoria).

## Instalación

En Windows puedes hacer doble clic en `instalar.bat` (crea el entorno, instala y verifica
dependencias, y repara el entorno si estuviera dañado). Manualmente:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Ejecución

```powershell
.\.venv\Scripts\python.exe seed.py   # opcional: reinicia y siembra la base de datos
.\.venv\Scripts\python.exe run.py    # http://127.0.0.1:5000
```

La aplicación crea el archivo `instance/la_epoca_de_oro.db` y lo siembra automáticamente si está vacío.

## Cuentas de prueba

| Usuario | Contraseña | Rol | Acceso |
|---|---|---|---|
| admin | admin123 | ADMIN | Todo el sistema |
| chef1 | chef123 | CHEF_SUPERVISOR | Cocina, inventario, mermas, recetas |
| chef2 | chef123 | CHEF_SUPERVISOR | Cocina, inventario, mermas, recetas |
| mesero1 | mesero123 | MESERO_POS | POS y comandas |
| mesero2 | mesero123 | MESERO_POS | POS y comandas |

Correos: `<usuario>@laepocadeoro.com` (se usan en la recuperación de contraseña).

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Estructura del proyecto

```
run.py                     Arranque del servidor
seed.py                    Reinicia y siembra la base de datos
app/
  __init__.py              Fábrica create_app(), filtros Jinja y manejadores de error
  config.py                Configuración (desarrollo / pruebas)
  constants.py             Constantes de dominio (roles, turnos, cuentas contables, etc.)
  security.py              Sesiones: login_required y role_required
  utilidades.py            Utilidades de fechas
  models/                  Entidades SQLAlchemy (dominio)
  repositories/            Acceso a datos (consultas por entidad)
  services/                Reglas de negocio y transacciones
  blueprints/              Controladores HTTP por módulo
  templates/               Vistas Jinja2
  static/                  CSS y JavaScript
  seed.py                  Datos iniciales (usuarios, insumos, recetas, catálogo)
tests/                     Suite pytest
docs/                      Prompt mejorado y reporte final
```

## Módulos

- **Autenticación**: login, recuperación de contraseña y administración de usuarios (solo ADMIN).
- **POS (meseros)**: turno mañana/tarde, carrito, modificador de guisados para tacos y tortas, selección de mesa, validación de stock, métodos de pago y ticket imprimible. Incluye panel de comandas pendientes con estado en vivo.
- **Mesas**: mapa del salón por zona (Interior, Terraza, Barra) con estados (libre, ocupada, reservada, limpieza) y liberación automática tras cerrar la comanda.
- **Cocina (chefs)**: comandas agrupadas por mesero, con auto-actualización (pulso), marca de lista → entrega → merma (con opción de cancelar la venta), historial y visor de insumos por comanda.
- **Insumos de cocina**: chefs reportan faltantes con un clic; el aviso aparece en el dashboard y se resuelve cuando llega el insumo.
- **Inventario**: 3 almacenes (ALM-MP, ALM-COC, ALM-POS), entradas con estado de pago, transferencias, mermas con motivo, alertas de stock mínimo y bitácora de movimientos.
- **Recetas (BOM)**: productos con receta por insumo/almacén; la venta descuenta insumos automáticamente. Cada tarjeta muestra stock disponible y "alcanza para ~N platillos".
- **Reportes (ADMIN)**: ventas por día, horas pico, top platillos, por turno, rendimiento por mesa y proyecciones, con gráficas.
- **Contabilidad**: libro diario con asientos automáticos (venta, compra, gasto, merma de insumo y de platillo, cancelación, nómina y pagos), gastos operativos, cuentas por pagar, estado de resultados real por turno y flujo de caja.
- **RRHH**: marcado rápido de jornada (entrada/retardo/salida con hora del servidor), registro manual, asistencias con validaciones y pago de nómina por periodo (sin doble pago).

## Documentación

- `docs/PROMPT_MEJORADO.md`: versión optimizada del prompt original.
- `docs/REPORTE_FINAL.md`: correcciones aplicadas, por qué y evidencia de verificación.
- `docs/ROADMAP.md`: ideas acordadas para después (lealtad, reservaciones, modo móvil, etc.).
