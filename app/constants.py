class Rol:
    ADMIN = "ADMIN"
    CHEF_SUPERVISOR = "CHEF_SUPERVISOR"
    MESERO_POS = "MESERO_POS"

    TODOS = (ADMIN, CHEF_SUPERVISOR, MESERO_POS)
    ETIQUETAS = {
        ADMIN: "Administrador",
        CHEF_SUPERVISOR: "Jefe de Cocina (Supervisor)",
        MESERO_POS: "Mesero (POS)",
    }


class Turno:
    MANANA = "MANANA"
    TARDE = "TARDE"
    TODOS = (MANANA, TARDE)
    ETIQUETAS = {MANANA: "Mañana", TARDE: "Tarde"}
    ICONOS = {MANANA: "☀️", TARDE: "🌙"}


class TipoOrden:
    AQUI = "AQUI"
    LLEVAR = "LLEVAR"
    ETIQUETAS = {AQUI: "Comer aquí", LLEVAR: "Para llevar"}
    ICONOS = {AQUI: "🍽️", LLEVAR: "🛍️"}


class MetodoPago:
    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
    TRANSFERENCIA = "TRANSFERENCIA"
    TODOS = (EFECTIVO, TARJETA, TRANSFERENCIA)
    ETIQUETAS = {
        EFECTIVO: "Efectivo",
        TARJETA: "Tarjeta de crédito/débito",
        TRANSFERENCIA: "Transferencia",
    }
    CUENTA_CONTABLE = {EFECTIVO: "1101", TARJETA: "1102", TRANSFERENCIA: "1102"}


class EstadoComanda:
    EN_PREPARACION = "EN_PREPARACION"
    LISTA = "LISTA"
    ENTREGADA = "ENTREGADA"
    ETIQUETAS = {
        EN_PREPARACION: "En preparación",
        LISTA: "Lista para entregar",
        ENTREGADA: "Entregada",
    }


class TipoMovimiento:
    ENTRADA = "ENTRADA"
    TRANSFERENCIA = "TRANSFERENCIA"
    SALIDA_VENTA = "SALIDA_VENTA"
    MERMA = "MERMA"
    ETIQUETAS = {
        ENTRADA: "Entrada (compra)",
        TRANSFERENCIA: "Transferencia entre almacenes",
        SALIDA_VENTA: "Salida por venta",
        MERMA: "Merma",
    }


class EstadoPago:
    PAGADO = "PAGADO"
    PENDIENTE = "PENDIENTE"
    NO_APLICA = "NO_APLICA"
    ETIQUETAS = {
        PAGADO: "Pagado",
        PENDIENTE: "Pendiente de pago",
        NO_APLICA: "No aplica",
    }


class EstadoAsistencia:
    PRESENTE = "PRESENTE"
    RETARDO = "RETARDO"
    FALTA = "FALTA"
    ETIQUETAS = {PRESENTE: "Presente", RETARDO: "Retardo", FALTA: "Falta"}
    PAGABLES = (PRESENTE, RETARDO)


MOTIVOS_MERMA = (
    "Alimento caducado",
    "Error de preparación",
    "Derrame o accidente",
    "Producto dañado en almacén",
    "Devolución de cliente",
    "Otro",
)

CATEGORIAS_GASTO = {
    "RENTA": ("6101", "Renta del local"),
    "GAS": ("6102", "Gas"),
    "LUZ": ("6103", "Luz (CFE)"),
    "AGUA": ("6104", "Agua"),
    "INTERNET": ("6105", "Internet y telefonía"),
    "LIMPIEZA": ("6106", "Artículos de limpieza"),
    "SOFTWARE": ("6107", "Hosting y software ERP"),
    "NOMINA": ("6201", "Nómina del personal"),
    "OTRO": ("6901", "Otros gastos operativos"),
}

CATALOGO_CUENTAS = (
    ("1101", "Caja (efectivo)", "ACTIVO"),
    ("1102", "Bancos (tarjeta/transferencia)", "ACTIVO"),
    ("1201", "Inventario de insumos", "ACTIVO"),
    ("2101", "Cuentas por pagar", "PASIVO"),
    ("3101", "Capital social", "CAPITAL"),
    ("4101", "Ventas del periodo", "INGRESO"),
    ("5101", "Costo de ventas (recetas/BOM)", "COSTO"),
    ("5102", "Mermas y desperdicios", "COSTO"),
    ("6101", "Gasto: Renta del local", "GASTO"),
    ("6102", "Gasto: Gas", "GASTO"),
    ("6103", "Gasto: Luz (CFE)", "GASTO"),
    ("6104", "Gasto: Agua", "GASTO"),
    ("6105", "Gasto: Internet y telefonía", "GASTO"),
    ("6106", "Gasto: Artículos de limpieza", "GASTO"),
    ("6107", "Gasto: Hosting y software ERP", "GASTO"),
    ("6201", "Gasto: Nómina del personal", "GASTO"),
    ("6901", "Gasto: Otros operativos", "GASTO"),
)

CUENTA_CAJA = "1101"
CUENTA_BANCOS = "1102"
CUENTA_INVENTARIO = "1201"
CUENTA_CXP = "2101"
CUENTA_VENTAS = "4101"
CUENTA_COSTO_VENTAS = "5101"
CUENTA_MERMAS = "5102"

GUISADOS = (
    "Chorizo",
    "Bistec",
    "Alambre",
    "Trocito de Puerco",
    "Chicharrón Prensado",
    "Barbacoa",
    "Huevo Rojo",
    "Huevo Verde",
)

GUISADO_A_INSUMO = {
    "Chorizo": "INS-GUI-CHO",
    "Bistec": "INS-GUI-BIS",
    "Alambre": "INS-GUI-ALA",
    "Trocito de Puerco": "INS-GUI-TRO",
    "Chicharrón Prensado": "INS-GUI-CHP",
    "Barbacoa": "INS-GUI-BAR",
    "Huevo Rojo": "INS-GUI-HUR",
    "Huevo Verde": "INS-GUI-HUV",
}

PORCION_GUISADO_KG = 0.12

HORA_CORTE_TURNO = 15
