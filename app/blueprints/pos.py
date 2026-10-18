import json

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from app.constants import Rol, Turno
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
    turno = request.args.get("turno", menu.turno_sugerido())
    if turno not in Turno.TODOS:
        turno = menu.turno_sugerido()

    return render_template(
        "pos/index.html",
        catalogo=menu.catalogo_por_turno(turno),
        turno=turno,
        turno_sugerido=menu.turno_sugerido(),
        guisados=menu.lista_guisados(),
        pedidos=VentaService().pedidos_del_mesero(g.usuario.id),
    )


@pos_bp.route("/confirmar", methods=["POST"])
@role_required(Rol.MESERO_POS, Rol.ADMIN)
def confirmar():
    turno = request.form.get("turno", "")
    try:
        items = json.loads(request.form.get("items_json", "[]"))
        venta = VentaService().registrar_venta(
            mesero_id=g.usuario.id,
            turno=turno,
            tipo_orden=request.form.get("tipo_orden", ""),
            metodo_pago=request.form.get("metodo_pago", ""),
            items=items,
            usuario_id=g.usuario.id,
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
