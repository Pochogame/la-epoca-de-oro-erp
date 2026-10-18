from datetime import date, datetime, time, timedelta


def parse_fecha(texto, por_defecto=None):
    if not texto:
        return por_defecto
    try:
        return datetime.strptime(texto.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return por_defecto


def rango_dia(fecha):
    return datetime.combine(fecha, time.min), datetime.combine(fecha, time.max)


def rango_fechas(desde, hasta):
    return datetime.combine(desde, time.min), datetime.combine(hasta, time.max)


def inicio_mes_actual():
    return date.today().replace(day=1)


def fin_mes_actual():
    hoy = date.today()
    siguiente_mes = hoy.replace(day=28) + timedelta(days=4)
    return siguiente_mes - timedelta(days=siguiente_mes.day)


def inicio_semana_actual():
    hoy = date.today()
    return hoy - timedelta(days=hoy.weekday())


def fin_semana_actual():
    return inicio_semana_actual() + timedelta(days=6)
