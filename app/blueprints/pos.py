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

from app.constants import EstadoComanda, Rol, TipoOrden, Turno
from app.extensions import db
from app.security import role_required
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

    return render_template(
        "pos/index.html",
        catalogo=menu.catalogo_por_turno(turno),
        turno=turno,
        turno_sugerido=menu.turno_sugerido(),
        guisados=menu.lista_guisados(),
        pedidos=ventas.pedidos_del_mesero(g.usuario.id),
        comandas_pendientes=ventas.comandas_pendientes_de(g.usuario.id),
        mesas=ventas.mesas_por_zona(),
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
        )
    except (ErrorDeNegocio, ValueError) as error:
        db.session.rollback()
        mensaje = getattr(error, "mensaje", "El pedido no pudo procesarse. Verifica los datos.")
        flash(mensaje, "error")
        return redirect(url_for("pos.index", turno=turno))
    else:
        flash(f"Venta {venta.folio} registrada y comanda enviada a cocina.", "exito")
        return redirect(url_for("pos.ticket", venta_id=venta.id))


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
                "hora": comanda.creada.strftime("%H:%M"),
                "tipo": TipoOrden.ETIQUETAS[comanda.tipo_orden],
                "total": f"${comanda.venta.total:,.2f}",
                "cerrable": comanda.estado in (EstadoComanda.ENTREGADA, EstadoComanda.MERMA),
            }
            for comanda in comandas
        ]
    )


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
