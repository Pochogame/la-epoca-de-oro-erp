import json
from datetime import date, datetime

from app.constants import EstadoAsistencia
from app.extensions import db
from app.models.rrhh import Asistencia, NominaPago
from app.repositories.rrhh_repository import AsistenciaRepositorio, NominaRepositorio
from app.repositories.usuario_repository import UsuarioRepositorio
from app.services.contabilidad_service import ContabilidadService
from app.services.excepciones import (
    DatosInvalidosError,
    OperacionDuplicadaError,
)


class RRHHService:
    def __init__(self, asistencias=None, nominas=None, usuarios=None, contabilidad=None):
        self.asistencias = asistencias or AsistenciaRepositorio()
        self.nominas = nominas or NominaRepositorio()
        self.usuarios = usuarios or UsuarioRepositorio()
        self.contabilidad = contabilidad or ContabilidadService()

    def registrar_asistencia(self, usuario_id, fecha, hora_entrada, hora_salida, estado):
        usuario = self.usuarios.obtener(usuario_id)
        if usuario is None or not usuario.activo:
            raise DatosInvalidosError("El trabajador indicado no existe o está inactivo.")
        if estado not in EstadoAsistencia.ETIQUETAS:
            raise DatosInvalidosError("El estado de asistencia no es válido.")
        if not isinstance(fecha, date):
            raise DatosInvalidosError("La fecha de asistencia no es válida.")
        if fecha > datetime.now().date():
            raise DatosInvalidosError("No se pueden registrar asistencias en fechas futuras.")

        if estado == EstadoAsistencia.FALTA:
            hora_entrada = None
            hora_salida = None
        elif hora_entrada and hora_salida and hora_salida <= hora_entrada:
            raise DatosInvalidosError("La hora de salida debe ser posterior a la hora de entrada.")

        asistencia = self.asistencias.del_dia(usuario_id, fecha)
        if asistencia is None:
            asistencia = Asistencia(usuario_id=usuario_id, fecha=fecha)
            self.asistencias.agregar(asistencia)
        asistencia.hora_entrada = hora_entrada
        asistencia.hora_salida = hora_salida
        asistencia.estado = estado
        db.session.commit()
        return asistencia

    def marcar_jornada(self, usuario_id, fecha, accion):
        usuario = self.usuarios.obtener(usuario_id)
        if usuario is None or not usuario.activo:
            raise DatosInvalidosError("El trabajador indicado no existe o está inactivo.")
        if accion not in ("entrada", "retardo", "salida"):
            raise DatosInvalidosError("La acción de asistencia no es válida.")
        if not isinstance(fecha, date) or fecha > datetime.now().date():
            raise DatosInvalidosError("La fecha de asistencia no es válida.")

        asistencia = self.asistencias.del_dia(usuario_id, fecha)
        if asistencia is None:
            asistencia = Asistencia(usuario_id=usuario_id, fecha=fecha)
            self.asistencias.agregar(asistencia)

        ahora = datetime.now().time().replace(second=0, microsecond=0)
        if accion == "salida":
            if asistencia.hora_entrada is None:
                raise DatosInvalidosError(
                    f"{usuario.nombre} no tiene hora de entrada registrada todavía."
                )
            if asistencia.hora_salida is not None:
                raise DatosInvalidosError(
                    f"{usuario.nombre} ya tiene salida registrada hoy "
                    f"({asistencia.hora_salida.strftime('%H:%M')})."
                )
            asistencia.hora_salida = ahora
            if asistencia.estado == EstadoAsistencia.FALTA:
                asistencia.estado = EstadoAsistencia.PRESENTE
        else:
            if asistencia.hora_entrada is not None:
                raise DatosInvalidosError(
                    f"{usuario.nombre} ya tiene entrada registrada hoy "
                    f"({asistencia.hora_entrada.strftime('%H:%M')}). "
                    "Usa el formulario manual si necesitas corregirla."
                )
            asistencia.hora_entrada = ahora
            asistencia.estado = (
                EstadoAsistencia.PRESENTE if accion == "entrada" else EstadoAsistencia.RETARDO
            )
        db.session.commit()
        return asistencia

    def listar_asistencias(self, desde, hasta, usuario_id=None):
        return self.asistencias.en_rango(desde, hasta, usuario_id)

    def calcular_nomina(self, desde, hasta):
        filas = []
        total_general = 0.0
        for usuario in self.usuarios.activos():
            asistencias = self.asistencias.en_rango(desde, hasta, usuario.id)
            dias_pagables = [
                a for a in asistencias if a.estado in EstadoAsistencia.PAGABLES
            ]
            faltas = [a for a in asistencias if a.estado == EstadoAsistencia.FALTA]
            total = round(usuario.sueldo_diario * len(dias_pagables), 2)
            total_general += total
            filas.append(
                {
                    "usuario": usuario,
                    "sueldo_diario": usuario.sueldo_diario,
                    "dias_trabajados": len(dias_pagables),
                    "faltas": len(faltas),
                    "total": total,
                }
            )
        return {"desde": desde, "hasta": hasta, "filas": filas, "total": round(total_general, 2)}

    def registrar_pago(self, desde, hasta, usuario_id=None):
        if self.nominas.del_periodo(desde, hasta):
            raise OperacionDuplicadaError(
                f"La nómina del periodo {desde} a {hasta} ya fue pagada anteriormente."
            )
        calculo = self.calcular_nomina(desde, hasta)
        if calculo["total"] <= 0:
            raise DatosInvalidosError(
                "No hay días trabajados registrados en el periodo. Captura asistencias primero."
            )
        gasto = self.contabilidad.registrar_gasto(
            "NOMINA",
            f"Nómina del {desde.strftime('%d/%m/%Y')} al {hasta.strftime('%d/%m/%Y')}",
            calculo["total"],
            usuario_id=usuario_id,
            autocommit=False,
        )
        nomina = NominaPago(
            desde=desde,
            hasta=hasta,
            total=calculo["total"],
            detalle_json=json.dumps(
                [
                    {
                        "trabajador": fila["usuario"].nombre,
                        "rol": fila["usuario"].rol,
                        "dias_trabajados": fila["dias_trabajados"],
                        "faltas": fila["faltas"],
                        "sueldo_diario": fila["sueldo_diario"],
                        "total": fila["total"],
                    }
                    for fila in calculo["filas"]
                ],
                ensure_ascii=False,
            ),
            gasto_id=gasto.id,
        )
        self.nominas.agregar(nomina)
        db.session.commit()
        return nomina

    def historial_pagos(self):
        return self.nominas.historial()
