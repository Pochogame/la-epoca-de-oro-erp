# Prompt mejorado — La Época de Oro ERP

Versión optimizada del archivo original `prompt.txt`. Corrige ambigüedades que permitieron
un prototipo sin persistencia, sin seguridad y con finanzas simuladas. Este prompt puede
reutilizarse tal cual para regenerar el sistema.

---

## Prompt optimizado

Genera un sistema ERP web completo, funcional y persistente en Python para la empresa
"La Época de Oro (Café, Guisados y Nostalgia)".

### 1. Stack y arquitectura (no negociable)

- Backend: Flask 3 + Flask-SQLAlchemy + SQLite (configurable a PostgreSQL por variable de
  entorno). Frontend: Jinja2 + Tailwind CSS + JavaScript vanilla. Sin servicios externos.
- Arquitectura por capas con carpetas separadas: `models/` (entidades), `repositories/`
  (acceso a datos), `services/` (reglas de negocio y transacciones), `blueprints/`
  (controladores HTTP), `templates/` y `static/` (presentación).
- Principios SOLID: una responsabilidad por clase, inyección de dependencias en
  constructores, constantes de dominio centralizadas, servicios sin conocimiento de HTTP.
- **Prohibido**: guardar datos de negocio (ventas, usuarios, comandas) en memoria de sesión
  o diccionarios del proceso. Todo dato de negocio vive en la base de datos.

### 2. Seguridad y control de acceso

- Contraseñas hasheadas (werkzeug.security). Nunca texto plano.
- Registro público deshabilitado: la creación de usuarios es exclusiva del rol ADMIN.
- Recuperación de contraseña validando usuario + correo registrado.
- RBAC aplicado en el servidor, ruta por ruta: cada endpoint valida rol; una petición no
  autorizada responde 403.
- 5 usuarios preconfigurados: admin/admin123 (ADMIN), chef1 y chef2/chef123
  (CHEF_SUPERVISOR), mesero1 y mesero2/mesero123 (MESERO_POS), con correos
  `<usuario>@laepocadeoro.com`.

### 3. Modelo de datos mínimo

Usuarios y roles; almacenes; insumos con costo unitario, unidad (kg/L/pza) y stock mínimo;
existencias por almacén; movimientos de inventario (entrada, transferencia, merma, salida
por venta) con costo y estado de pago; mermas con motivo; productos por turno con precio;
recetas (BOM) producto-insumo-almacén-cantidad; ventas con folio, turno, método de pago y
desglose; comandas con estados; asistencias; pagos de nómina; catálogo de cuentas
contable; asientos y líneas (partida doble); gastos operativos con estado de pago.

### 4. Inventario, almacenes y recetas

- 3 almacenes: ALM-MP (materia prima), ALM-COC (cocina/barra), ALM-POS (mostrador).
- Entradas de compra (con estado PAGADO/PENDIENTE), transferencias entre almacenes y mermas
  con motivo; alertas de stock mínimo por insumo.
- Cada producto tiene receta con insumos y cantidades. Al vender se valida stock y se
  descuenta automáticamente del almacén de consumo correspondiente. Si no hay stock, la
  venta se rechaza con mensaje claro (no se permite stock negativo).
- Guisados de tacos y tortas: catálogo cerrado
  (Chorizo, Bistec, Alambre, Trocito de Puerco, Chicharrón Prensado, Barbacoa, Huevo Rojo,
  Huevo Verde), cada uno mapeado a un insumo real con porción definida.

### 5. Menú por turnos

- Turno Mañana: cafés, frappés/smoothies, panadería (conchas, cuernitos, carlotas,
  cupcakes, brownies) y almuerzos (chilaquiles rojos/verdes, huevos rojo/verde, molletes).
- Turno Tarde: pozole rojo/verde, menudo, orden de tacos, torta tradicional.
- Regla estricta: un producto del turno contrario se rechaza al vender.

### 6. POS y comandas

- Pantalla ágil con selección de turno Mañana/Tarde, búsqueda por categoría, carrito con
  cantidades y total en vivo, modificador emergente de guisado para tacos/tortas.
- Al confirmar: folio consecutivo, venta persistida, comanda creada (estado EN_PREPARACION),
  descuento de insumos y asiento contable, todo en una sola transacción.
- Pantalla de cocina (chefs): comandas en preparación, marcar LISTA y DESPACHAR; el
  historial queda en la base de datos (jamás se borra una venta).
- Métodos de pago: Efectivo, Tarjeta, Transferencia. Ticket imprimible con logo textual,
  folio, fecha, turno, mesero, desglose, total y método de pago.

### 7. Contabilidad real (prohibida la simulación aleatoria)

- Partida doble obligatoria y cuadrada en cada asiento, con folio consecutivo.
- Asientos automáticos: venta (caja/ingresos + costo de ventas/inventario), compra a
  crédito o contado (inventario vs cuentas por pagar o caja), gasto operativo, merma,
  pago de cuentas por pagar y pago de nómina.
- Gastos operativos con categorías: Renta, Gas, Luz, Agua, Internet, Limpieza y Nómina,
  con estado PAGADO/PENDIENTE y acción "pagar".
- Estado de Resultados calculado de transacciones reales en un rango de fechas: ventas
  desglosadas Mañana vs Tarde, costo de ventas, utilidad bruta, mermas, gastos, nómina y
  utilidad neta.
- Flujo de caja: saldos de caja y bancos, cuentas por pagar y compras pendientes.
- Queda prohibido usar números aleatorios o tablas fijas para reportes financieros.

### 8. RRHH (solo ADMIN)

- Registro de asistencia por trabajador y fecha; validar: sin fechas futuras, hora de
  salida posterior a la de entrada, duplicado del día se actualiza.
- Cálculo de nómina del periodo por días pagables (PRESENTE/RETARDO) según sueldo diario.
- Pago de nómina: genera el gasto contable, registra el pago y bloquea doble pago del
  mismo periodo.

### 9. Calidad

- Suite de pruebas pytest (integración con base de datos en memoria) cubriendo: login y
  roles (403), venta con descuento de stock, rechazo por falta de stock, turnos, guisados,
  asiento cuadrado por venta, estado de resultados, CxP, asistencia y nómina.
- Datos sembrados de demostración: catálogo de insumos y productos con precios plausibles
  en MXN, recetas completas y usuarios de prueba.
- Montos en MXN con 2 decimales; fechas y horas legibles en español.

### 10. Estilo visual

- Clásico, cálido y nostálgico: tonos crema, terracota, café y madera, inspirado en el
  cine de oro mexicano y el sabor de hogar. El ticket y las pantallas de cocina deben ser
  legibles a distancia.

### 11. Entregables

- Código ejecutable con un solo comando (`python run.py`), script de siembra idempotente,
  README con instalación, cuentas de prueba y estructura, y reporte de decisiones.
