# La Época de Oro ERP

Sistema ERP + POS para "La Época de Oro (Café, Guisados y Nostalgia)": punto de venta por turnos con tamaños de producto, comandas a cocina, inventario único con recetas (BOM), CRM básico de clientes, contabilidad de partida doble, RRHH con nómina y control de acceso por roles.

## Stack

- Python 3.10+ con Flask 3, Flask-SQLAlchemy y SQLite (sin servicios externos).
- Jinja2 + Tailwind CSS (CDN) + JavaScript vanilla para el carrito del POS y gráficas (Chart.js CDN por página).
- pytest para las pruebas (75 pruebas de integración con base de datos en memoria).

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

La aplicación crea el archivo `instance/la_epoca_de_oro.db` y lo siembra automáticamente si está vacío. Al arrancar también aplica migraciones idempotentes (columnas y tablas nuevas, consolidación del almacén principal y sincronización del catálogo).

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
- **POS (meseros)**: turno mañana/tarde, carrito, modificador de guisados para tacos y tortas, selección de tamaño para pozole, menudo y aguas, selección de mesa y cliente, validación de stock con aviso de faltantes parciales (permite quitar líneas y continuar), métodos de pago y ticket imprimible. Incluye panel de comandas pendientes con estado en vivo.
- **Cuentas de mesa por rondas**: cada mesa puede acumular varias rondas/adiciones aunque no sean seguidas; cocina ve solo la ronda nueva. La cuenta puede asociarse a un cliente y conserva esa asociación en todas sus rondas. El cobro se registra una sola vez al cerrar la cuenta (con ticket consolidado) y hasta entonces se reconoce el ingreso. Los platillos ya enviados pueden cancelarse con contraseña de administrador: se descuentan de la cuenta y cocina recibe un aviso de cancelación.
- **Mesas**: mapa del salón por zona (Interior, Terraza, Barra) con estados (libre, ocupada, reservada, limpieza) y cuenta abierta visible; la mesa pasa a limpieza al cobrar la cuenta.
- **Cocina (chefs)**: comandas agrupadas por mesero, con auto-actualización (pulso), marca de ronda/adición, avisos de cancelación autorizada, marca de lista → entrega → merma (con opción de cancelar la venta), historial y visor de insumos por comanda.
- **Insumos de cocina**: chefs reportan faltantes con un clic; el aviso aparece en el dashboard y se resuelve cuando llega el insumo.
- **Inventario**: un solo almacén principal, entradas con estado de pago, mermas con motivo, alertas de stock mínimo y bitácora de movimientos. Las bases existentes consolidan automáticamente el stock de los almacenes anteriores.
- **Recetas (BOM)**: productos con receta por insumo; la venta descuenta insumos automáticamente y escala la receta según el tamaño elegido. Menú editable con precios, disponibilidad y tamaños (chico/mediano/grande, medio/litro). Cada tarjeta muestra stock disponible y "alcanza para ~N platillos".
- **CRM (ADMIN)**: directorio de clientes con teléfono único, cumpleaños, notas e historial de compras; muestra visitas, total consumido, ticket promedio y última compra. El POS permite asociar un cliente a una venta o cuenta sin salir del flujo de cobro.
- **Reportes (ADMIN)**: ventas por día, horas pico, top platillos, por turno, rendimiento por mesa y proyecciones, con gráficas.
- **Contabilidad**: libro diario con asientos automáticos (venta, compra, gasto, merma de insumo y de platillo, cancelación, nómina y pagos), gastos operativos, cuentas por pagar, estado de resultados real por turno y flujo de caja.
- **RRHH**: marcado rápido de jornada (entrada/retardo/salida con hora del servidor), registro manual, asistencias con validaciones y pago de nómina por periodo (sin doble pago).

## Documentación

- `docs/PROMPT_MEJORADO.md`: versión optimizada del prompt original.
- `docs/REPORTE_FINAL.md`: correcciones aplicadas, por qué y evidencia de verificación.
- `docs/ROADMAP.md`: ideas acordadas para después (lealtad, reservaciones, modo móvil, etc.).
