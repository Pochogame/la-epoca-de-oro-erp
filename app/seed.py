from datetime import date, datetime, time, timedelta

from app.constants import (
    CATALOGO_CUENTAS,
    EstadoAsistencia,
    EstadoComanda,
    EstadoPago,
    Rol,
    Turno,
)
from app.extensions import db
from app.models.contabilidad import CuentaContable
from app.models.crm import Cliente
from app.models.inventario import Almacen, Insumo, StockAlmacen
from app.models.menu import Producto, ProductoVariante, RecetaIngrediente
from app.models.usuario import Usuario
from app.models.ventas import Mesa
from app.services.contabilidad_service import ContabilidadService
from app.services.rrhh_service import RRHHService
from app.services.venta_service import VentaService

USUARIOS_SEMILLA = (
    {
        "username": "admin",
        "password": "admin123",
        "nombre": "Administrador General",
        "email": "admin@laepocadeoro.com",
        "rol": Rol.ADMIN,
        "sueldo_diario": 450.0,
    },
    {
        "username": "chef1",
        "password": "chef123",
        "nombre": "Chef Supervisor A",
        "email": "chef1@laepocadeoro.com",
        "rol": Rol.CHEF_SUPERVISOR,
        "sueldo_diario": 500.0,
    },
    {
        "username": "chef2",
        "password": "chef123",
        "nombre": "Chef Supervisor B",
        "email": "chef2@laepocadeoro.com",
        "rol": Rol.CHEF_SUPERVISOR,
        "sueldo_diario": 500.0,
    },
    {
        "username": "mesero1",
        "password": "mesero123",
        "nombre": "Mesero A",
        "email": "mesero1@laepocadeoro.com",
        "rol": Rol.MESERO_POS,
        "sueldo_diario": 350.0,
    },
    {
        "username": "mesero2",
        "password": "mesero123",
        "nombre": "Mesero B",
        "email": "mesero2@laepocadeoro.com",
        "rol": Rol.MESERO_POS,
        "sueldo_diario": 350.0,
    },
)

ALMACENES_SEMILLA = (
    ("ALM-MP", "Almacén principal", "Inventario único de insumos y productos."),
)

INSUMOS_SEMILLA = (
    ("INS-CAF", "Café molido", "kg", 280.0, 1.0, 15.0, 0.0, 3.0),
    ("INS-LEC", "Leche entera", "L", 26.0, 4.0, 30.0, 10.0, 6.0),
    ("INS-CHO", "Chocolate para bebida", "kg", 190.0, 0.5, 4.0, 0.5, 0.5),
    ("INS-HIE", "Hielo", "kg", 12.0, 5.0, 0.0, 15.0, 15.0),
    ("INS-FRE", "Fresa", "kg", 90.0, 1.0, 0.0, 5.0, 0.0),
    ("INS-MAN", "Mango", "kg", 60.0, 1.0, 0.0, 5.0, 0.0),
    ("INS-LCO", "Leche condensada", "kg", 65.0, 0.5, 4.0, 0.0, 1.0),
    ("INS-ORE", "Galleta Oreo (paquete de 9)", "pza", 18.0, 2.0, 10.0, 0.0, 2.0),
    ("INS-V12", "Vaso 12 oz", "pza", 2.5, 50.0, 0.0, 0.0, 300.0),
    ("INS-V16", "Vaso 16 oz", "pza", 3.0, 50.0, 0.0, 0.0, 300.0),
    ("INS-TAP", "Tapa para vaso", "pza", 0.9, 100.0, 0.0, 0.0, 600.0),
    ("INS-CUC", "Cuchara / popote desechable", "pza", 0.5, 100.0, 0.0, 0.0, 600.0),
    ("INS-SER", "Servilleta", "pza", 0.25, 200.0, 0.0, 0.0, 1000.0),
    ("INS-CON", "Contenedor para llevar", "pza", 4.5, 40.0, 0.0, 0.0, 150.0),
    ("INS-PCO", "Concha (pieza)", "pza", 12.0, 10.0, 0.0, 0.0, 40.0),
    ("INS-PCU", "Cuernito (pieza)", "pza", 15.0, 8.0, 0.0, 0.0, 30.0),
    ("INS-PCL", "Carlota de limón (rebanada)", "pza", 20.0, 6.0, 0.0, 0.0, 20.0),
    ("INS-PCC", "Cupcake (pieza)", "pza", 22.0, 6.0, 0.0, 0.0, 20.0),
    ("INS-PBR", "Brownie (pieza)", "pza", 24.0, 6.0, 0.0, 0.0, 20.0),
    ("INS-TOT", "Totopos de maíz", "kg", 60.0, 2.0, 15.0, 5.0, 0.0),
    ("INS-SAL", "Salsa de chile (base)", "kg", 45.0, 2.0, 10.0, 4.0, 0.0),
    ("INS-QUE", "Queso fresco", "kg", 180.0, 2.0, 12.0, 4.0, 0.0),
    ("INS-CRE", "Crema ácida", "L", 60.0, 1.0, 8.0, 3.0, 0.0),
    ("INS-CEB", "Cebolla blanca", "kg", 25.0, 2.0, 10.0, 3.0, 0.0),
    ("INS-HUE", "Huevo", "pza", 3.5, 60.0, 300.0, 60.0, 0.0),
    ("INS-TOR", "Tortilla de maíz", "kg", 22.0, 5.0, 40.0, 12.0, 0.0),
    ("INS-BOL", "Bolillo", "pza", 4.0, 10.0, 0.0, 0.0, 60.0),
    ("INS-FRI", "Frijoles cocidos", "kg", 40.0, 2.0, 8.0, 3.0, 0.0),
    ("INS-MAY", "Mayonesa", "kg", 45.0, 1.0, 4.0, 1.0, 0.0),
    ("INS-MAI", "Maíz pozolero", "kg", 35.0, 3.0, 20.0, 6.0, 0.0),
    ("INS-POL", "Pollo para pozole", "kg", 95.0, 4.0, 20.0, 6.0, 0.0),
    ("INS-GUA", "Chile guajillo", "kg", 90.0, 0.5, 3.0, 0.5, 0.0),
    ("INS-PAN", "Pancita para menudo", "kg", 180.0, 2.0, 10.0, 4.0, 0.0),
    ("INS-ORO", "Orégano seco", "kg", 320.0, 0.2, 1.0, 0.2, 0.0),
    ("INS-LECH", "Lechuga", "pza", 12.0, 3.0, 15.0, 4.0, 0.0),
    ("INS-TOS", "Tostadas", "pza", 1.5, 30.0, 200.0, 60.0, 0.0),
    ("INS-TEL", "Pan telera", "pza", 8.0, 10.0, 0.0, 0.0, 50.0),
    ("INS-LIM", "Limón", "kg", 30.0, 1.0, 5.0, 1.0, 1.0),
    ("INS-GUI-CHO", "Guisado: chorizo", "kg", 140.0, 2.0, 0.0, 12.0, 0.0),
    ("INS-GUI-BIS", "Guisado: bistec", "kg", 260.0, 2.0, 0.0, 12.0, 0.0),
    ("INS-GUI-ALA", "Guisado: alambre", "kg", 230.0, 2.0, 0.0, 12.0, 0.0),
    ("INS-GUI-TRO", "Guisado: trocito de puerco", "kg", 190.0, 2.0, 0.0, 12.0, 0.0),
    ("INS-GUI-CHP", "Guisado: chicharrón prensado", "kg", 160.0, 2.0, 0.0, 10.0, 0.0),
    ("INS-GUI-BAR", "Guisado: barbacoa", "kg", 380.0, 2.0, 0.0, 10.0, 0.0),
    ("INS-GUI-HUR", "Guisado: huevo en salsa roja", "kg", 90.0, 1.0, 0.0, 12.0, 0.0),
    ("INS-GUI-HUV", "Guisado: huevo en salsa verde", "kg", 90.0, 1.0, 0.0, 12.0, 0.0),
    ("INS-REF-SAN", "Refresco Sangría (botella)", "pza", 15.0, 6.0, 0.0, 0.0, 24.0),
    ("INS-REF-PEP", "Refresco Pepsi (botella)", "pza", 15.0, 6.0, 0.0, 0.0, 24.0),
    ("INS-REF-FRE", "Refresco Fresca (botella)", "pza", 15.0, 6.0, 0.0, 0.0, 24.0),
    ("INS-REF-MIR", "Refresco Mirinda (botella)", "pza", 15.0, 6.0, 0.0, 0.0, 24.0),
    ("INS-AGU-JAM", "Flor de jamaica", "kg", 120.0, 0.5, 1.0, 0.5, 1.0),
    ("INS-ARR", "Arroz para horchata", "kg", 25.0, 1.0, 3.0, 1.0, 1.5),
    ("INS-CAN", "Canela en raja", "kg", 200.0, 0.2, 0.5, 0.2, 0.5),
    ("INS-PEP", "Pepino", "kg", 18.0, 2.0, 4.0, 2.0, 2.0),
    ("INS-AZU", "Azúcar", "kg", 22.0, 2.0, 8.0, 3.0, 4.0),
)

PRODUCTOS_SEMILLA = (
    (
        "BEB-CAF-AM", "Café Americano", "Bebidas Calientes", 35.0, Turno.MANANA, False, "ALM-POS",
        (("INS-CAF", 0.020), ("INS-V12", 1), ("INS-TAP", 1), ("INS-CUC", 1), ("INS-SER", 1)),
    ),
    (
        "BEB-LATTE", "Latte", "Bebidas Calientes", 45.0, Turno.MANANA, False, "ALM-POS",
        (("INS-CAF", 0.018), ("INS-LEC", 0.20), ("INS-V12", 1), ("INS-TAP", 1), ("INS-SER", 1)),
    ),
    (
        "BEB-CAPUCHINO", "Capuchino", "Bebidas Calientes", 50.0, Turno.MANANA, False, "ALM-POS",
        (
            ("INS-CAF", 0.018), ("INS-LEC", 0.15), ("INS-CHO", 0.02),
            ("INS-V12", 1), ("INS-TAP", 1), ("INS-SER", 1),
        ),
    ),
    (
        "BEB-ESPRESSO", "Espresso", "Bebidas Calientes", 30.0, Turno.MANANA, False, "ALM-POS",
        (("INS-CAF", 0.015), ("INS-V12", 1), ("INS-TAP", 1)),
    ),
    (
        "FRI-FRAP-MOKA", "Frappé Moka", "Barra Fría (Frappés y Smoothies)", 65.0, Turno.MANANA, False, "ALM-POS",
        (
            ("INS-CAF", 0.020), ("INS-LEC", 0.20), ("INS-HIE", 0.25), ("INS-CHO", 0.03),
            ("INS-V16", 1), ("INS-TAP", 1), ("INS-CUC", 1),
        ),
    ),
    (
        "FRI-FRAP-OREO", "Frappé Oreo", "Barra Fría (Frappés y Smoothies)", 65.0, Turno.MANANA, False, "ALM-POS",
        (
            ("INS-LEC", 0.20), ("INS-HIE", 0.25), ("INS-ORE", 1),
            ("INS-V16", 1), ("INS-TAP", 1), ("INS-CUC", 1),
        ),
    ),
    (
        "FRI-SMO-FRUTS", "Smoothie Frutos Rojos", "Barra Fría (Frappés y Smoothies)", 60.0, Turno.MANANA, False, "ALM-POS",
        (("INS-FRE", 0.15), ("INS-LEC", 0.15), ("INS-HIE", 0.20), ("INS-V16", 1), ("INS-TAP", 1)),
    ),
    (
        "FRI-SMO-MANGO", "Smoothie Mango", "Barra Fría (Frappés y Smoothies)", 60.0, Turno.MANANA, False, "ALM-POS",
        (("INS-MAN", 0.20), ("INS-LEC", 0.15), ("INS-HIE", 0.20), ("INS-V16", 1), ("INS-TAP", 1)),
    ),
    (
        "PAN-CONCHA", "Concha Tradicional", "Panadería y Repostería", 20.0, Turno.MANANA, False, "ALM-POS",
        (("INS-PCO", 1),),
    ),
    (
        "PAN-CUERNITO", "Cuernito", "Panadería y Repostería", 25.0, Turno.MANANA, False, "ALM-POS",
        (("INS-PCU", 1),),
    ),
    (
        "PAN-CARLOTA", "Carlota de Limón", "Panadería y Repostería", 35.0, Turno.MANANA, False, "ALM-POS",
        (("INS-PCL", 1),),
    ),
    (
        "PAN-CUPCAKE", "Cupcake", "Panadería y Repostería", 38.0, Turno.MANANA, False, "ALM-POS",
        (("INS-PCC", 1),),
    ),
    (
        "PAN-BROWNIE", "Brownie", "Panadería y Repostería", 40.0, Turno.MANANA, False, "ALM-POS",
        (("INS-PBR", 1),),
    ),
    (
        "ALM-CHILAQUILES", "Chilaquiles Verdes o Rojos", "Almuerzos Caseros", 85.0, Turno.MANANA, False, "ALM-COC",
        (
            ("INS-TOT", 0.15), ("INS-SAL", 0.10), ("INS-QUE", 0.04), ("INS-CRE", 0.04),
            ("INS-CEB", 0.02), ("INS-HUE", 1),
        ),
    ),
    (
        "ALM-HUEVOS", "Huevos en Salsa (Roja o Verde)", "Almuerzos Caseros", 75.0, Turno.MANANA, False, "ALM-COC",
        (("INS-HUE", 3), ("INS-SAL", 0.08), ("INS-TOR", 0.05), ("INS-FRI", 0.10)),
    ),
    (
        "ALM-MOLLETES", "Molletes", "Almuerzos Caseros", 60.0, Turno.MANANA, False, "ALM-COC",
        (("INS-BOL", 1), ("INS-FRI", 0.08), ("INS-QUE", 0.05)),
    ),
    (
        "TAR-POZOLE", "Pozole Rojo o Verde", "Platillos de Cuchara", 95.0, Turno.TARDE, False, "ALM-COC",
        (
            ("INS-MAI", 0.20), ("INS-POL", 0.15), ("INS-GUA", 0.02), ("INS-ORO", 0.002),
            ("INS-CEB", 0.02), ("INS-LECH", 0.05), ("INS-TOS", 2), ("INS-LIM", 0.02),
        ),
    ),
    (
        "TAR-MENUDO", "Menudo Tradicional", "Platillos de Cuchara", 110.0, Turno.TARDE, False, "ALM-COC",
        (
            ("INS-PAN", 0.20), ("INS-MAI", 0.15), ("INS-GUA", 0.02), ("INS-ORO", 0.002),
            ("INS-CEB", 0.02), ("INS-LIM", 0.02),
        ),
    ),
    (
        "TAR-TACOS", "Taco (por pieza)", "Antojitos (Tacos y Tortas)", 13.0, Turno.TARDE, True, "ALM-COC",
        (("INS-TOR", 0.05), ("INS-CEB", 0.003), ("INS-LIM", 0.003)),
    ),
    (
        "TAR-TORTA", "Torta Tradicional de Guisado", "Antojitos (Tacos y Tortas)", 65.0, Turno.TARDE, True, "ALM-COC",
        (("INS-TEL", 1), ("INS-MAY", 0.02)),
    ),
    (
        "TAR-REF-SAN", "Sangría", "Refrescos", 30.0, Turno.TARDE, False, "ALM-POS",
        (("INS-REF-SAN", 1), ("INS-HIE", 0.15), ("INS-V16", 1)),
    ),
    (
        "TAR-REF-PEP", "Pepsi", "Refrescos", 30.0, Turno.TARDE, False, "ALM-POS",
        (("INS-REF-PEP", 1), ("INS-HIE", 0.15), ("INS-V16", 1)),
    ),
    (
        "TAR-REF-FRE", "Fresca", "Refrescos", 30.0, Turno.TARDE, False, "ALM-POS",
        (("INS-REF-FRE", 1), ("INS-HIE", 0.15), ("INS-V16", 1)),
    ),
    (
        "TAR-REF-MIR", "Mirinda", "Refrescos", 30.0, Turno.TARDE, False, "ALM-POS",
        (("INS-REF-MIR", 1), ("INS-HIE", 0.15), ("INS-V16", 1)),
    ),
    (
        "TAR-AGU-JAM", "Agua de Jamaica", "Aguas Frescas", 35.0, Turno.TARDE, False, "ALM-POS",
        (
            ("INS-AGU-JAM", 0.02), ("INS-AZU", 0.02), ("INS-HIE", 0.20),
            ("INS-V16", 1), ("INS-TAP", 1), ("INS-CUC", 1),
        ),
    ),
    (
        "TAR-AGU-HOR", "Agua de Horchata", "Aguas Frescas", 35.0, Turno.TARDE, False, "ALM-POS",
        (
            ("INS-ARR", 0.03), ("INS-CAN", 0.002), ("INS-AZU", 0.02), ("INS-HIE", 0.20),
            ("INS-V16", 1), ("INS-TAP", 1), ("INS-CUC", 1),
        ),
    ),
    (
        "TAR-AGU-PEP", "Agua de Pepino con Limón", "Aguas Frescas", 35.0, Turno.TARDE, False, "ALM-POS",
        (
            ("INS-PEP", 0.10), ("INS-LIM", 0.03), ("INS-AZU", 0.02), ("INS-HIE", 0.20),
            ("INS-V16", 1), ("INS-TAP", 1), ("INS-CUC", 1),
        ),
    ),
)

MESAS_SEMILLA = (
    (1, "Salón principal"), (2, "Salón principal"), (3, "Salón principal"),
    (4, "Salón principal"), (5, "Salón principal"), (6, "Salón principal"),
    (7, "Terraza"), (8, "Terraza"), (9, "Terraza"), (10, "Terraza"),
    (11, "Barra"), (12, "Barra"),
)

VARIANTES_SEMILLA = {
    "TAR-POZOLE": (
        ("Chico", 80.0, 0.75),
        ("Mediano", 95.0, 1.0),
        ("Grande", 110.0, 1.3),
    ),
    "TAR-MENUDO": (
        ("Chico", 95.0, 0.75),
        ("Mediano", 110.0, 1.0),
        ("Grande", 125.0, 1.3),
    ),
    "TAR-AGU-JAM": (("Medio", 20.0, 0.5), ("Litro", 35.0, 1.0)),
    "TAR-AGU-HOR": (("Medio", 20.0, 0.5), ("Litro", 35.0, 1.0)),
    "TAR-AGU-PEP": (("Medio", 20.0, 0.5), ("Litro", 35.0, 1.0)),
}

CLIENTES_SEMILLA = (
    ("María López", "4771234567", "maria.lopez@example.com", date(1990, 5, 14), "Prefiere mesa de terraza."),
    ("Carlos Ramírez", "4779876543", "carlos.ramirez@example.com", date(1985, 11, 2), "Cliente frecuente de comida corrida."),
    ("Ana Torres", "4775551234", "ana.torres@example.com", date(1998, 8, 21), "Pide pozole sin cebolla."),
)


def _crear_usuarios():
    for datos in USUARIOS_SEMILLA:
        usuario = Usuario(
            username=datos["username"],
            nombre=datos["nombre"],
            email=datos["email"],
            rol=datos["rol"],
            sueldo_diario=datos["sueldo_diario"],
        )
        usuario.definir_password(datos["password"])
        db.session.add(usuario)
    db.session.commit()


def _crear_almacenes():
    for codigo, nombre, descripcion in ALMACENES_SEMILLA:
        db.session.add(Almacen(codigo=codigo, nombre=nombre, descripcion=descripcion))
    db.session.commit()


def _crear_insumos_y_stock():
    principal = Almacen.query.filter_by(codigo="ALM-MP").first()
    for codigo, nombre, unidad, costo, minimo, stock_mp, stock_coc, stock_pos in INSUMOS_SEMILLA:
        insumo = Insumo(
            codigo=codigo,
            nombre=nombre,
            unidad=unidad,
            costo_unitario=costo,
            stock_minimo=minimo,
        )
        db.session.add(insumo)
        db.session.flush()
        total = stock_mp + stock_coc + stock_pos
        if total > 0:
            db.session.add(
                StockAlmacen(
                    insumo_id=insumo.id,
                    almacen_id=principal.id,
                    cantidad=total,
                )
            )
    db.session.commit()


def _crear_variantes(producto, variantes):
    for orden, (nombre, precio, factor) in enumerate(variantes):
        existente = ProductoVariante.query.filter_by(
            producto_id=producto.id, nombre=nombre
        ).first()
        if existente is not None:
            continue
        db.session.add(
            ProductoVariante(
                producto_id=producto.id,
                nombre=nombre,
                precio=precio,
                factor_receta=factor,
                orden=orden,
            )
        )


def _crear_productos_y_recetas():
    principal = Almacen.query.filter_by(codigo="ALM-MP").first()
    insumos = {insumo.codigo: insumo for insumo in Insumo.query.all()}
    for codigo, nombre, categoria, precio, turno, requiere_guisado, _, receta in PRODUCTOS_SEMILLA:
        producto = Producto(
            codigo=codigo,
            nombre=nombre,
            categoria=categoria,
            precio=precio,
            turno=turno,
            requiere_guisado=requiere_guisado,
            almacen_consumo_id=principal.id,
        )
        db.session.add(producto)
        db.session.flush()
        for insumo_codigo, cantidad in receta:
            db.session.add(
                RecetaIngrediente(
                    producto_id=producto.id,
                    insumo_id=insumos[insumo_codigo].id,
                    cantidad=cantidad,
                )
            )
        _crear_variantes(producto, VARIANTES_SEMILLA.get(codigo, ()))
    db.session.commit()


def _crear_clientes():
    for nombre, telefono, email, cumpleanos, notas in CLIENTES_SEMILLA:
        if Cliente.query.filter_by(telefono=telefono).first() is not None:
            continue
        db.session.add(
            Cliente(
                nombre=nombre,
                telefono=telefono,
                email=email,
                cumpleanos=cumpleanos,
                notas=notas,
            )
        )
    db.session.commit()


def _crear_mesas():
    for numero, zona in MESAS_SEMILLA:
        db.session.add(Mesa(numero=numero, zona=zona))
    db.session.commit()


def _crear_catalogo_contable():
    for codigo, nombre, tipo in CATALOGO_CUENTAS:
        db.session.add(CuentaContable(codigo=codigo, nombre=nombre, tipo=tipo))
    db.session.commit()


def _crear_gastos_ejemplo(admin_id):
    contabilidad = ContabilidadService()
    contabilidad.registrar_gasto(
        "RENTA", "Renta del local (mes en curso)", 25000.0,
        estado=EstadoPago.PENDIENTE, usuario_id=admin_id,
    )
    contabilidad.registrar_gasto(
        "LUZ", "Recibo CFE (bimestral)", 1800.0, usuario_id=admin_id,
        estado=EstadoPago.PAGADO,
    )
    contabilidad.registrar_gasto(
        "INTERNET", "Internet y telefonía del mes", 899.0, usuario_id=admin_id,
        estado=EstadoPago.PAGADO,
    )
    contabilidad.registrar_gasto(
        "SOFTWARE", "Hosting y software ERP", 350.0, usuario_id=admin_id,
        estado=EstadoPago.PAGADO,
    )
    contabilidad.registrar_gasto(
        "LIMPIEZA", "Artículos de limpieza", 950.0, usuario_id=admin_id,
        estado=EstadoPago.PAGADO,
    )


def _crear_asistencias_ejemplo():
    rrhh = RRHHService()
    hoy = datetime.now().date()
    usuarios = Usuario.query.order_by(Usuario.id).all()
    for usuario in usuarios:
        for dias_atras in range(1, 7):
            fecha = hoy - timedelta(days=dias_atras)
            es_domingo = fecha.weekday() == 6
            if es_domingo:
                continue
            if usuario.username == "chef2" and dias_atras == 3:
                rrhh.registrar_asistencia(usuario.id, fecha, None, None, EstadoAsistencia.FALTA)
                continue
            if usuario.username == "mesero2" and dias_atras == 5:
                rrhh.registrar_asistencia(
                    usuario.id, fecha, time(7, 45), time(15, 45), EstadoAsistencia.RETARDO
                )
                continue
            entrada = time(7, 55) if usuario.es_mesero else time(8, 0)
            salida = time(15, 55) if usuario.es_mesero else time(16, 0)
            rrhh.registrar_asistencia(
                usuario.id, fecha, entrada, salida, EstadoAsistencia.PRESENTE
            )


def _crear_ventas_ejemplo(admin_id):
    ventas = VentaService()
    productos = {producto.codigo: producto for producto in Producto.query.all()}
    clientes = {cliente.nombre: cliente for cliente in Cliente.query.all()}

    ventas_demo = (
        (
            "mesero1", Turno.MANANA, "AQUI", "EFECTIVO", "María López",
            (
                {"producto_id": productos["BEB-CAF-AM"].id, "cantidad": 2},
                {"producto_id": productos["PAN-CONCHA"].id, "cantidad": 3},
            ),
        ),
        (
            "mesero2", Turno.MANANA, "LLEVAR", "TARJETA", "Carlos Ramírez",
            (
                {"producto_id": productos["FRI-FRAP-MOKA"].id, "cantidad": 1},
                {"producto_id": productos["PAN-CUERNITO"].id, "cantidad": 2},
            ),
        ),
        (
            "mesero1", Turno.TARDE, "AQUI", "EFECTIVO", "Ana Torres",
            (
                {"producto_id": productos["TAR-TACOS"].id, "cantidad": 3, "guisado": "Barbacoa"},
                {"producto_id": productos["TAR-POZOLE"].id, "cantidad": 1, "variante_nombre": "Grande"},
            ),
        ),
    )

    meseros = {usuario.username: usuario for usuario in Usuario.query.all()}
    for username, turno, tipo, metodo, cliente_nombre, items in ventas_demo:
        venta = ventas.registrar_venta(
            mesero_id=meseros[username].id,
            turno=turno,
            tipo_orden=tipo,
            metodo_pago=metodo,
            items=list(items),
            usuario_id=meseros[username].id,
            cliente_id=clientes[cliente_nombre].id if cliente_nombre in clientes else None,
        )
        comanda = venta.comanda
        comanda.estado = EstadoComanda.ENTREGADA
        comanda.lista_en = comanda.creada
        comanda.entregada_en = comanda.creada
        comanda.cerrada_en = comanda.creada
    db.session.commit()


def seed_database(reset=False):
    if reset:
        db.drop_all()
        db.create_all()

    if Usuario.query.count() > 0:
        return False

    _crear_usuarios()
    _crear_almacenes()
    _crear_insumos_y_stock()
    _crear_productos_y_recetas()
    _crear_clientes()
    _crear_mesas()
    _crear_catalogo_contable()
    admin = Usuario.query.filter_by(username="admin").first()
    _crear_gastos_ejemplo(admin.id)
    _crear_asistencias_ejemplo()
    _crear_ventas_ejemplo(admin.id)
    return True


def sincronizar_catalogo():
    """Agrega a bases existentes lo nuevo del catálogo (insumos, productos, mesas)
    sin tocar los datos ya capturados. Es idempotente."""
    if Usuario.query.count() == 0:
        return False

    cambios = False
    principal = Almacen.query.filter_by(codigo="ALM-MP").first()
    if principal is None:
        principal = Almacen.query.order_by(Almacen.id).first()
    if principal is None:
        return False

    for codigo, nombre, unidad, costo, minimo, stock_mp, stock_coc, stock_pos in INSUMOS_SEMILLA:
        if Insumo.query.filter_by(codigo=codigo).first() is not None:
            continue
        insumo = Insumo(
            codigo=codigo, nombre=nombre, unidad=unidad, costo_unitario=costo, stock_minimo=minimo
        )
        db.session.add(insumo)
        db.session.flush()
        total = stock_mp + stock_coc + stock_pos
        if total > 0:
            db.session.add(
                StockAlmacen(
                    insumo_id=insumo.id,
                    almacen_id=principal.id,
                    cantidad=total,
                )
            )
        cambios = True

    insumos = {insumo.codigo: insumo for insumo in Insumo.query.all()}
    for codigo, nombre, categoria, precio, turno, requiere_guisado, _, receta in PRODUCTOS_SEMILLA:
        producto = Producto.query.filter_by(codigo=codigo).first()
        if producto is not None:
            if (
                codigo == "TAR-TACOS"
                and producto.nombre == "Orden de Tacos (3 pzas)"
                and producto.precio == 75.0
            ):
                producto.nombre = nombre
                producto.precio = precio
                db.session.flush()
                for insumo_codigo, cantidad in receta:
                    linea = RecetaIngrediente.query.filter_by(
                        producto_id=producto.id, insumo_id=insumos[insumo_codigo].id
                    ).first()
                    if linea is not None:
                        linea.cantidad = cantidad
                cambios = True
            if codigo in VARIANTES_SEMILLA and not producto.variantes:
                _crear_variantes(producto, VARIANTES_SEMILLA[codigo])
                cambios = True
            if producto.almacen_consumo_id != principal.id:
                producto.almacen_consumo_id = principal.id
                cambios = True
            continue
        producto = Producto(
            codigo=codigo,
            nombre=nombre,
            categoria=categoria,
            precio=precio,
            turno=turno,
            requiere_guisado=requiere_guisado,
            almacen_consumo_id=principal.id,
        )
        db.session.add(producto)
        db.session.flush()
        for insumo_codigo, cantidad in receta:
            db.session.add(
                RecetaIngrediente(
                    producto_id=producto.id,
                    insumo_id=insumos[insumo_codigo].id,
                    cantidad=cantidad,
                )
            )
        _crear_variantes(producto, VARIANTES_SEMILLA.get(codigo, ()))
        cambios = True

    if Mesa.query.count() == 0:
        _crear_mesas()
        cambios = True

    if cambios:
        db.session.commit()
    return cambios
