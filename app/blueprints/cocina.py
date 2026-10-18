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

from app.constants import MOTIVOS_MERMA_COMANDA, Rol
from app.extensions import db
from app.security import role_required
from app.services.excepciones import ErrorDeNegocio
from app.services.inventario_service import InventarioService
from app.services.venta_service import VentaService

cocina_bp = Blueprint("cocina", __name__, url_prefix="/cocina")


def _firma_comandas(comandas):
    return "|".join(f"{comanda.id}:{comanda.estado}" for comanda in comandas)


@cocina_bp.route("/")
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def index():
    ventas = VentaService()
    inventario = InventarioService()
    comandas = ventas.comandas_activas()
    return render_template(
        "cocina/index.html",
        comandas=comandas,
        firma=_firma_comandas(comandas),
        historial=ventas.historial_comandas(10),
        avisos=inventario.avisos_pendientes(),
        motivos_merma=MOTIVOS_MERMA_COMANDA,
    )


@cocina_bp.route("/pulso")
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def pulso():
    comandas = VentaService().comandas_activas()
    return jsonify({"activas": len(comandas), "firma": _firma_comandas(comandas)})


@cocina_bp.route("/comanda/<int:comanda_id>")
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def comanda_detalle(comanda_id):
    detalle = VentaService().detalle_comanda(comanda_id)
    if detalle is None:
        abort(404)
    return render_template(
        "cocina/comanda_detalle.html",
        avisos=[aviso.insumo_id for aviso in InventarioService().avisos_pendientes()],
        **detalle,
    )


@cocina_bp.route("/comanda/<int:comanda_id>/listo", methods=["POST"])
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def marcar_listo(comanda_id):
    try:
        VentaService().marcar_comanda_lista(comanda_id)
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        flash("Comanda marcada como lista para entregar.", "exito")
    return redirect(url_for("cocina.index"))


@cocina_bp.route("/comanda/<int:comanda_id>/entregar", methods=["POST"])
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def despachar(comanda_id):
    try:
        VentaService().marcar_comanda_entregada(comanda_id)
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        flash("Comanda entregada. El mesero puede cerrarla desde su POS.", "exito")
    return redirect(url_for("cocina.index"))


@cocina_bp.route("/comanda/<int:comanda_id>/merma", methods=["POST"])
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def merma(comanda_id):
    motivo = request.form.get("motivo", MOTIVOS_MERMA_COMANDA[0])
    if motivo not in MOTIVOS_MERMA_COMANDA:
        motivo = MOTIVOS_MERMA_COMANDA[0]
    cancelar_venta = request.form.get("cancelar_venta") == "1"
    try:
        VentaService().marcar_comanda_merma(
            comanda_id, motivo, cancelar_venta=cancelar_venta, usuario_id=g.usuario.id
        )
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        accion = "y la venta fue cancelada" if cancelar_venta else "conservando la venta"
        flash(f"Platillo registrado como merma ({motivo.lower()}) {accion}.", "exito")
    return redirect(url_for("cocina.index"))


@cocina_bp.route("/insumos")
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def insumos():
    inventario = InventarioService()
    return render_template(
        "cocina/insumos.html",
        filas=inventario.insumos_de_almacen("ALM-COC"),
        avisos=inventario.avisos_pendientes(),
    )


@cocina_bp.route("/insumos/<int:insumo_id>/avisar", methods=["POST"])
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def avisar_faltante(insumo_id):
    try:
        InventarioService().avisar_faltante(
            insumo_id, usuario_id=g.usuario.id, comentario=request.form.get("comentario", "")
        )
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        flash("Aviso registrado: el insumo se marca como faltante.", "exito")
    return redirect(url_for("cocina.insumos"))


@cocina_bp.route("/insumos/aviso/<int:aviso_id>/resolver", methods=["POST"])
@role_required(Rol.CHEF_SUPERVISOR, Rol.ADMIN)
def resolver_faltante(aviso_id):
    try:
        InventarioService().resolver_faltante(aviso_id, usuario_id=g.usuario.id)
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        flash("Aviso resuelto: el insumo ya está disponible.", "exito")
    return redirect(request.form.get("volver") or url_for("cocina.insumos"))
