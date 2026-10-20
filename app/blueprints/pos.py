import json

from flask import (
    Blueprint,
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from app.constants import EstadoComanda, MetodoPago, Rol, TipoOrden, Turno
from app.extensions import db
from app.security import role_required
from app.services.crm_service import ClienteService
from app.services.excepciones import ErrorDeNegocio
from app.services.menu_service import MenuService
from app.services.venta_service import VentaService

pos_bp = Blueprint("pos", __name__, url_prefix="/pos")


@pos_bp.route("/")
@role_required(Rol.MESERO_POS, Rol.ADMIN)
def index():
    menu = MenuService()
    ventas = VentaService()
    turno = request.args.get("turno", menu.turno_sugerido())
    if turno not in Turno.TODOS:
        turno = menu.turno_sugerido()

    mesa_param = request.args.get("mesa", type=int)
    cuentas_abiertas = ventas.cuentas_abiertas_por_mesa()
    cuenta_actual = cuentas_abiertas.get(mesa_param) if mesa_param else None

    return render_template(
        "pos/index.html",
        catalogo=menu.catalogo_por_turno(turno),
        turno=turno,
        turno_sugerido=menu.turno_sugerido(),
        guisados=menu.lista_guisados(),
        pedidos=ventas.pedidos_del_mesero(g.usuario.id),
        comandas_pendientes=ventas.comandas_pendientes_de(g.usuario.id),
        mesas=ventas.mesas_por_zona(),
        cuentas_abiertas=cuentas_abiertas,
        cuenta_actual=cuenta_actual,
        clientes=ClienteService().activos(),
    )


@pos_bp.route("/confirmar", methods=["POST"])
@role_required(Rol.MESERO_POS, Rol.ADMIN)
def confirmar():
    turno = request.form.get("turno", "")
    try:
        items = json.loads(request.form.get("items_json", "[]"))
        mesa_id = request.form.get("mesa_id") or None
        venta = VentaService().registrar_venta(
            mesero_id=g.usuario.id,
            turno=turno,
            tipo_orden=request.form.get("tipo_orden", ""),
            metodo_pago=request.form.get("metodo_pago", ""),
            items=items,
            usuario_id=g.usuario.id,
            mesa_id=mesa_id,
            cliente_id=request.form.get("cliente_id", type=int),
            agregar_a_cuenta=request.form.get("agregar_a_cuenta") == "1",
        )
    except (ErrorDeNegocio, ValueError, TypeError) as error:
        db.session.rollback()
        mensaje = getattr(error, "mensaje", "El pedido no pudo procesarse. Verifica los datos.")
        flash(mensaje, "error")
        return redirect(url_for("pos.index", turno=turno))
    else:
        if venta.cuenta_id:
            flash(
                f"Ronda {venta.comanda.ronda} agregada a la cuenta de la mesa "
                f"{venta.mesa.numero}. Se cobra al cerrar la cuenta.",
                "exito",
            )
            return redirect(url_for("pos.cuenta_detalle", cuenta_id=venta.cuenta_id))
        flash(f"Venta {venta.folio} registrada y comanda enviada a cocina.", "exito")
        return redirect(url_for("pos.ticket", venta_id=venta.id))


@pos_bp.route("/disponibilidad", methods=["POST"])
@role_required(Rol.MESERO_POS, Rol.ADMIN)
def disponibilidad():
    datos = request.get_json(silent=True) or {}
    turno = datos.get("turno", "")
    if turno not in Turno.TODOS:
        return jsonify({"error": "El turno no es válido."}), 400
    try:
        resultado = VentaService().evaluar_disponibilidad(
            datos.get("items") or [], turno
        )
    except (ErrorDeNegocio, ValueError, TypeError) as error:
        mensaje = getattr(error, "mensaje", "No se pudo revisar la disponibilidad.")
        return jsonify({"error": mensaje}), 400
    return jsonify(resultado)


@pos_bp.route("/ticket/<int:venta_id>")
@role_required(Rol.MESERO_POS, Rol.ADMIN)
def ticket(venta_id):
    venta = VentaService().venta_de(venta_id)
    if venta is None:
        abort(404)
    if venta.mesero_id != g.usuario.id and not g.usuario.es_admin:
        abort(403)
    return render_template("pos/ticket.html", venta=venta)


@pos_bp.route("/comanda/<int:comanda_id>")
@role_required(Rol.MESERO_POS, Rol.ADMIN)
def comanda_detalle(comanda_id):
    ventas = VentaService()
    detalle = ventas.detalle_comanda(comanda_id)
    if detalle is None:
        abort(404)
    comanda = detalle["comanda"]
    if comanda.venta.mesero_id != g.usuario.id and not g.usuario.es_admin:
        abort(403)
    return render_template("pos/comanda_detalle.html", **detalle)


@pos_bp.route("/comanda/<int:comanda_id>/cerrar", methods=["POST"])
@role_required(Rol.MESERO_POS, Rol.ADMIN)
def cerrar_comanda(comanda_id):
    try:
        VentaService().cerrar_comanda(comanda_id, usuario_id=g.usuario.id)
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        flash("Comanda cerrada y retirada de tus pedidos pendientes.", "exito")
    return redirect(request.form.get("volver") or url_for("pos.index"))


@pos_bp.route("/comandas-estado")
@role_required(Rol.MESERO_POS, Rol.ADMIN)
def comandas_estado():
    comandas = VentaService().comandas_pendientes_de(g.usuario.id)
    return jsonify(
        [
            {
                "id": comanda.id,
                "folio": comanda.folio,
                "estado": comanda.estado,
                "etiqueta": EstadoComanda.ETIQUETAS[comanda.estado],
                "mesa": comanda.venta.mesa.numero if comanda.venta.mesa else None,
                "ronda": comanda.ronda,
                "cuenta": comanda.venta.cuenta_id is not None,
                "hora": comanda.creada.strftime("%H:%M"),
                "tipo": TipoOrden.ETIQUETAS[comanda.tipo_orden],
                "total": f"${comanda.venta.total:,.2f}",
                "por_cobrar": comanda.venta.por_cobrar,
                "cerrable": comanda.estado in (EstadoComanda.ENTREGADA, EstadoComanda.MERMA),
            }
            for comanda in comandas
        ]
    )


@pos_bp.route("/cuenta/<int:cuenta_id>")
@role_required(Rol.MESERO_POS, Rol.ADMIN)
def cuenta_detalle(cuenta_id):
    detalle = VentaService().detalle_cuenta(cuenta_id)
    if detalle is None:
        flash("La cuenta ya no existe o fue cobrada desde otro dispositivo.", "error")
        return redirect(url_for("pos.mesas"))
    return render_template(
        "pos/cuenta.html", clientes=ClienteService().activos(), **detalle
    )


@pos_bp.route("/cuenta/<int:cuenta_id>/cobrar", methods=["POST"])
@role_required(Rol.MESERO_POS, Rol.ADMIN)
def cobrar_cuenta(cuenta_id):
    ventas = VentaService()
    try:
        cliente_id = request.form.get("cliente_id", type=int)
        if cliente_id:
            ventas.asignar_cliente_cuenta(cuenta_id, cliente_id)
        ventas.cobrar_cuenta(
            cuenta_id,
            request.form.get("metodo_pago", ""),
            usuario_id=g.usuario.id,
        )
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
        return redirect(url_for("pos.cuenta_detalle", cuenta_id=cuenta_id))
    flash("Cuenta cobrada. La mesa quedó lista para limpieza.", "exito")
    return redirect(url_for("pos.cuenta_ticket", cuenta_id=cuenta_id))


@pos_bp.route("/cuenta/<int:cuenta_id>/ticket")
@role_required(Rol.MESERO_POS, Rol.ADMIN)
def cuenta_ticket(cuenta_id):
    detalle = VentaService().detalle_cuenta(cuenta_id)
    if detalle is None:
        flash("La cuenta ya no existe o fue cobrada desde otro dispositivo.", "error")
        return redirect(url_for("pos.mesas"))
    return render_template("pos/cuenta_ticket.html", **detalle)


@pos_bp.route("/detalle/<int:detalle_id>/cancelar", methods=["POST"])
@role_required(Rol.MESERO_POS, Rol.ADMIN)
def cancelar_detalle(detalle_id):
    volver = request.form.get("volver", "")
    if not volver.startswith("/"):
        volver = url_for("pos.index")
    try:
        VentaService().cancelar_detalle(
            detalle_id,
            request.form.get("motivo", ""),
            request.form.get("password_admin", ""),
            usuario_id=g.usuario.id,
        )
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        flash(
            "Platillo cancelado y retirado de la cuenta. Cocina recibió el aviso.",
            "exito",
        )
    return redirect(volver)


@pos_bp.route("/mesas")
@role_required(Rol.MESERO_POS, Rol.ADMIN)
def mesas():
    return render_template("pos/mesas.html", zonas=VentaService().mesas_por_zona())


@pos_bp.route("/mesas/<int:mesa_id>/estado", methods=["POST"])
@role_required(Rol.MESERO_POS, Rol.ADMIN)
def cambiar_estado_mesa(mesa_id):
    try:
        mesa = VentaService().cambiar_estado_mesa(mesa_id, request.form.get("estado", ""))
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        flash(f"Mesa {mesa.numero} ahora está: {mesa.estado.lower()}.", "exito")
    return redirect(url_for("pos.mesas"))
