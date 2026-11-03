# La Época de Oro · Sistema de gestión para restaurante

**Prototipo funcional de ERP + POS para cafeterías, fondas y restaurantes.**

Este proyecto concentra en una sola aplicación web la operación diaria de un negocio de
alimentos: toma de pedidos, cuentas por mesa, comandas a cocina, control de inventario con
recetas, historial de clientes, contabilidad y personal. Está pensado como una demostración
ejecutable de una herramienta hecha a la medida, sin depender de servicios externos ni de
configuraciones complejas.

---

## Ver la demo en 3 pasos (Windows 10/11)

1. Descarga el proyecto: botón verde **Code → Download ZIP** (o clona el repositorio).
2. Descomprime el archivo ZIP.
3. Haz doble clic en **`iniciar.bat`**.

La primera vez, el sistema:

- Instala Python 3.10 o superior automáticamente con `winget` si no está en el equipo.
- Crea un entorno virtual e instala las dependencias.
- Genera la base de datos con datos de demostración.
- Abre el navegador en `http://127.0.0.1:5000`.

> La primera ejecución puede tardar unos minutos. Las siguientes son inmediatas.

Si algo falla, ejecuta **`si_no_funciona_ejecuta_esto.bat`**: elimina el entorno, lo reinstala
y vuelve a iniciar el sistema.

### Instalación manual (opcional)

También puedes preparar el entorno manualmente. Requiere Python 3.10 o superior instalado y
con la casilla *"Add python.exe to PATH"* activada.

```powershell
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe seed.py
.\.venv\Scripts\python.exe run.py
```

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python seed.py
python run.py
```

## Cuentas de prueba

| Usuario | Contraseña | Rol | Acceso |
|---|---|---|---|
| `admin` | `admin123` | Administrador | Todo el sistema |
| `chef1` | `chef123` | Chef / supervisor | Cocina, inventario, mermas, recetas |
| `chef2` | `chef123` | Chef / supervisor | Cocina, inventario, mermas, recetas |
| `mesero1` | `mesero123` | Mesero / POS | Punto de venta y comandas |
| `mesero2` | `mesero123` | Mesero / POS | Punto de venta y comandas |

Correos de recuperación: `<usuario>@laepocadeoro.com`.

## Qué incluye

- **Punto de venta por turnos** con carrito, tamaños de producto, guisados para tacos y
  tortas, métodos de pago y ticket imprimible.
- **Cuentas por mesa y rondas**: varias adiciones en una misma cuenta, una ronda puede ser
  *para llevar* sin perder el vínculo con la mesa, cobro consolidado y cancelación autorizada
  de platillos.
- **Comandas a cocina** con estados en vivo (preparación, lista, entregada), mermas con motivo
  y visor de insumos por comanda.
- **Mapa de mesas** por zona, con estados de libre, ocupada, reservada y limpieza.
- **Inventario con recetas (BOM)**: un almacén principal, entradas, mermas, alertas de stock
  mínimo y descuento automático de insumos al vender.
- **CRM de clientes**: historial de compras, visitas, ticket promedio, cumpleaños y notas.
- **Reportes de ventas**: por día, por turno, horas pico, platillos más vendidos, rendimiento
  por mesa y proyecciones.
- **Contabilidad de partida doble**: asientos automáticos, gastos, cuentas por pagar, estado
  de resultados y flujo de caja.
- **Recursos humanos**: marcado de jornada, asistencias, incidencias y pago de nómina.

## Módulos

| Módulo | Descripción |
|---|---|
| Autenticación | Login, recuperación de contraseña y administración de usuarios (solo administrador). |
| POS | Pedidos por turno, modificadores, tamaños, cliente, mesa y validación de existencias. |
| Cuentas y mesas | Rondas, adiciones, cuentas por cobrar, cobro consolidado y mapa del salón. |
| Cocina | Comandas agrupadas por mesero, actualización automática, mermas e historial. |
| Inventario | Almacén principal, entradas, movimientos, mínimos y trazabilidad. |
| Recetas | Costeo y descuento automático de insumos por platillo y tamaño. |
| CRM | Directorio, métricas e historial de clientes. |
| Reportes | Ventas, turnos, horas pico, platillos y rendimiento por mesa. |
| Contabilidad | Libro diario, gastos, cuentas por pagar y estados financieros. |
| RRHH | Jornadas, asistencias, incidencias y nómina. |

## Stack tecnológico

- **Backend:** Python 3.10+ con Flask 3 y SQLAlchemy 2.
- **Base de datos:** SQLite local (sin servicios externos).
- **Frontend:** Jinja2, Tailwind CSS (CDN) y JavaScript vanilla; Chart.js para gráficas.
- **Pruebas:** pytest con base de datos en memoria.
- **Arquitectura:** capas separadas de modelos, repositorios, servicios y controladores HTTP.

## Estructura del proyecto

```
run.py                      Arranque del servidor
seed.py                     Reinicia y siembra la base de datos
iniciar.bat                 Instala si hace falta y arranca el sistema
instalar.bat                Instala Python (winget), entorno y dependencias
si_no_funciona_ejecuta_esto.bat  Reparación completa del entorno
probar.bat                  Ejecuta la suite de pruebas
empaquetar.bat              Genera un ZIP limpio para compartir
app/
  __init__.py               Fábrica create_app(), filtros y manejo de errores
  config.py                 Configuración de desarrollo y pruebas
  constants.py              Constantes de dominio (roles, turnos, cuentas)
  security.py               Control de sesión y permisos por rol
  models/                   Entidades SQLAlchemy
  repositories/             Consultas y acceso a datos
  services/                 Reglas de negocio y transacciones
  blueprints/               Controladores HTTP por módulo
  templates/                Vistas Jinja2
  static/                   CSS y JavaScript
tests/                      Suite de pruebas de integración
docs/                       Documentación técnica y roadmap
instance/                   Base de datos local (se crea automáticamente)
```

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

También puedes hacer doble clic en `probar.bat`. Estado actual: **78 pruebas de integración
en verde**, con verificación de migraciones idempotentes sobre la base de datos.

## Datos de demostración

Al arrancar por primera vez, el sistema crea la base `instance/la_epoca_de_oro.db` y carga:

- Usuarios y roles de ejemplo.
- Insumos, recetas y catálogo de productos con precios y tamaños.
- Mesas por zona y clientes de ejemplo.
- Ventas y movimientos para que los reportes y el dashboard tengan información visible.

Puedes reiniciar la demostración en cualquier momento con:

```powershell
.\.venv\Scripts\python.exe seed.py
```

## Alcance y notas

- Es un **prototipo funcional** de demostración, no una versión endurecida para producción.
- Los datos viven en un archivo SQLite local dentro de `instance/`; nada sale del equipo.
- El servidor escucha en `0.0.0.0:5000`, por lo que también puedes abrirlo desde otra
  computadora o tablet en la misma red usando la IP del equipo (por ejemplo,
  `http://192.168.1.20:5000`).
- Para un despliegue público o multi-sucursal se recomienda migrar a un servidor de
  aplicaciones con base de datos centralizada, respaldos y HTTPS.
- El proyecto se entrega sin datos reales del negocio.

## Documentación

- [`docs/REPORTE_FINAL.md`](docs/REPORTE_FINAL.md): decisiones técnicas y evidencia de verificación.
- [`docs/ROADMAP.md`](docs/ROADMAP.md): siguientes módulos sugeridos (lealtad, reservaciones,
  facturación, impresión térmica, cobro dividido, respaldos automáticos).
- [`docs/PROMPT_MEJORADO.md`](docs/PROMPT_MEJORADO.md): alcance original del sistema.
