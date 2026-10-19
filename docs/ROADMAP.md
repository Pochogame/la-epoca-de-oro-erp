# Roadmap — La Época de Oro ERP

Ideas acordadas con el equipo. No forman parte de la entrega actual; se implementan
en iteraciones posteriores, en este orden sugerido.

## 1. Lealtad "Boletos de Oro"

- La base de CRM (directorio, historial y asociación de cliente en POS/cuentas) ya está implementada.
- Tarjeta digital de cliente frecuente: 1 boleto por cada $X de consumo.
- Acumulación por teléfono (sin app): el mesero captura el teléfono en el POS.
- N boletos = platillo o bebida cortesía; canje registrado como gasto de marketing.
- Estado de cuenta del cliente consultable en caja.

## 2. Reservaciones de mesas

- Agenda por mesa/fecha/hora desde el mapa de mesas (estado "Reservada" ya existe).
- Aviso en POS si la mesa reservada intenta ocuparse fuera de su ventana.
- Recordatorio impreso o por WhatsApp (enlace manual, sin API).

## 3. Modo móvil (PWA) para meseros

- Vista POS optimizada para celular/tablet: botones grandes, carrito lateral.
- Instalable en pantalla de inicio; funciona con la red local del negocio.
- Notificaciones de "comanda lista" para el mesero (polling corto).

## 4. Impresión térmica de comandas y tickets

- Impresión directa (ESC/POS) o "Imprimir" del navegador con formato 58/80 mm.
- Copia para cocina (solo platillos) y copia para cliente (totales).

## 5. Corte de caja por turno

- Arqueo al cierre del turno: fondo inicial, ventas por método, retiros y diferencia.
- Asiento contable automático del corte y reporte imprimible.

## 6. Menús y precios por temporada

- Programar precios y disponibilidad por rango de fechas (menú de Cuaresma, Navidad).
- Precio promocional por hora (happy hour) sobre productos seleccionados.

## 7. Facturación y cumplimiento

- Datos fiscales básicos del negocio y folios por serie.
- Exportación de ventas a CSV/Excel para el contador.

## 8. Respaldos automáticos

- Copia diaria de `instance/la_epoca_de_oro.db` a una carpeta o USB.
- Restauración guiada desde el panel de administración.

## 9. Cuentas de mesa avanzadas

- Cobro dividido: asignar platillos o montos a varias personas/métodos de pago.
- Transferir una cuenta completa a otra mesa o unir mesas.
- Propina sugerida/editable al cobrar la cuenta.
