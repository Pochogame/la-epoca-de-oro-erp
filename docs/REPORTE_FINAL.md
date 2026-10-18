# Reporte final — Reconstrucción de "La Época de Oro ERP"

## Resumen ejecutivo

El sistema original (`Cafeycomida.txt`) era un prototipo monolítico de Streamlit que no
cumplía varios requisitos del propio prompt: no tenía persistencia, no aplicaba roles, no
tenía inventario ni contabilidad real, y presentaba "finanzas" generadas con números
aleatorios. Se reconstruyó completo como una aplicación Flask por capas (45 pruebas en
verde y verificación HTTP real) conservando el concepto visual, el menú, los turnos, los
roles y las cuentas de acceso solicitadas.

## Problemas del código original y cómo se corrigieron

| # | Problema en `Cafeycomida.txt` | Por qué es incorrecto | Corrección aplicada |
|---|---|---|---|
| 1 | Todos los datos en `st.session_state` (usuarios, ventas, comandas) | Se pierden al reiniciar o recargar; el prompt pedía base de datos | Modelo relacional completo en SQLite persistente (`instance/la_epoca_de_oro.db`) |
| 2 | Contraseñas en texto plano en un diccionario del código | Cualquiera con acceso al código o a la sesión conoce las claves | Hash con `werkzeug.security` (`generar_hash` / `verificar_hash`) |
| 3 | Registro público de usuarios con rol seleccionable, incluido ADMIN | Cualquier visitante podía crearse un administrador | Registro público eliminado; alta de usuarios solo por ADMIN en `/admin/usuarios` |
| 4 | Sin RBAC: los 5 roles veían las 4 pestañas (meseros veían finanzas y nómina) | El prompt exige acceso por perfil | `login_required` + `role_required` en cada endpoint; 403 verificado por pruebas |
| 5 | "Simulación financiera" con `np.random.seed(42)` que fabrica 60 días de ventas | Reportes falsos: no reflejan nada real; el prompt pide contabilidad real | Contabilidad de partida doble real; todo reporte se calcula de transacciones registradas |
| 6 | Nómina diaria de $2,150 y "Replit $350/mes" hardcodeados en el P&L | Montos inventados dentro del estado de resultados | Estado de resultados suma gastos reales por categoría; la nómina sale de asistencias y sueldos configurados |
| 7 | No existe inventario, almacenes, recetas (BOM) ni mermas; un `st.info` afirma que "descuenta automáticamente" | El requisito central del prompt no estaba implementado | 3 almacenes, existencias por almacén, entradas, transferencias, mermas con motivo, alertas de mínimo y descuento automático por receta al vender |
| 8 | No hay libro diario, asientos, gastos operativos, CxP ni flujo de caja | Requisitos explícitos del módulo contable | Asientos automáticos cuadrados (venta, compra, gasto, merma, nómina, pagos), catálogo de cuentas, gastos PAGADO/PENDIENTE y flujo de caja con cuentas por pagar |
| 9 | Comandas identificadas con `len(comandas_activas)+1` y borrado destructivo | Folios duplicados tras despachar y pérdida de historial de venta | Comandas y ventas con folio consecutivo en BD; estados EN_PREPARACION → LISTA → ENTREGADA; nada se borra |
| 10 | Menú y precios hardcodeados en la interfaz; guisados como texto libre | No es un catálogo administrable y no había validación | Catálogo en BD por turno/categoría; guisados en catálogo cerrado mapeado a insumos reales con porción |
| 11 | Sin ticket de venta (el prompt lo pedía con logo) | Requisito incumplido | Ticket imprimible con logo textual, folio, fecha, turno, mesero, desglose, total y método de pago |
| 12 | Sin pruebas ni separación de archivos (monolito de 374 líneas) | Imposible de mantener o verificar | Arquitectura por capas y suite pytest de 45 pruebas de integración |
| 13 | Recuperación de contraseña sin ninguna verificación adicional | Cualquiera con usuario+correo cambiaba la clave | Se conserva el flujo pedido por el prompt, pero sobre contraseñas hasheadas y validando ambas credenciales |

## Arquitectura implementada (SOLID)

- `app/models/`: entidades SQLAlchemy (dominio puro con validaciones de datos).
- `app/repositories/`: una clase por entidad, único punto de acceso a la base de datos.
- `app/services/`: reglas de negocio y transacciones; reciben repositorios por constructor
  (inyección de dependencias) y no conocen Flask ni HTTP.
- `app/blueprints/`: controladores delgados; traducen formularios a llamadas de servicio y
  errores de negocio a mensajes flash.
- `app/constants.py`: constantes de dominio centralizadas (roles, turnos, estados, cuentas).
- `app/security.py`: decoradores de sesión y rol aplicados uniformemente.

Ejemplos de reglas de oro respetadas: una sola responsabilidad por clase; abierto/cerrado
para nuevas categorías de gasto o productos (datos, no código); sustitución de repositorios
en pruebas sin tocar servicios; transacciones atómicas (venta = stock + comanda + asiento).

## Verificación

1. **Suite de pruebas**: `45 passed` con `.\.venv\Scripts\python.exe -m pytest -q`.
   Cubre autenticación y roles, venta con descuento de receta, rechazo por stock
   insuficiente, reglas de turno, guisados válidos, asiento cuadrado por venta, estado de
   resultados con ventas reales, cuentas por pagar, asistencia y nómina.
2. **Smoke test con servidor real** (`python` + `app.run`, puerto 5000):
   - `GET /login` → 200.
   - `POST /login` (admin/admin123) → dashboard con "Panel General".
   - `GET /pos/` → 200.
   - `GET /contabilidad/flujo-caja` → 200, mostrando compras pendientes.
3. **Siembra**: `python seed.py` reinicia y siembra la base sin errores.

Durante el desarrollo, la propia suite detectó y permitió corregir tres defectos internos:
una colisión de nombres en `RRHHService` (método y repositorio con el mismo atributo), el
uso del repositorio de insumos para pagar compras (debía ser el de movimientos) y el acceso
a movimientos desde el repositorio equivocado. Todos quedaron cubiertos por pruebas.

## Cuentas de prueba

| Usuario | Contraseña | Rol |
|---|---|---|
| admin | admin123 | ADMIN |
| chef1 | chef123 | CHEF_SUPERVISOR |
| chef2 | chef123 | CHEF_SUPERVISOR |
| mesero1 | mesero123 | MESERO_POS |
| mesero2 | mesero123 | MESERO_POS |

## Cómo ejecutar

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe seed.py
.\.venv\Scripts\python.exe run.py    # http://127.0.0.1:5000
```

## Notas y limitaciones

- La recuperación de contraseña valida usuario + correo contra la base de datos, pero no
  envía correos (no hay servidor SMTP); es el mismo alcance funcional del prompt original,
  ahora sobre credenciales hasheadas.
- SQLite es suficiente para la demostración; la configuración admite PostgreSQL cambiando
  la URL de conexión en `app/config.py`.
- La nómina considera días pagables (PRESENTE y RETARDO); se puede extender con deducciones
  si se requiere.
