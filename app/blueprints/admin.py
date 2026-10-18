from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from app.constants import Rol
from app.extensions import db
from app.security import role_required
from app.services.auth_service import AuthService
from app.services.excepciones import ErrorDeNegocio

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _servicio():
    return AuthService()


@admin_bp.route("/usuarios", methods=["GET", "POST"])
@role_required(Rol.ADMIN)
def usuarios():
    servicio = _servicio()
    if request.method == "POST":
        try:
            servicio.crear_usuario(
                username=request.form.get("username", ""),
                nombre=request.form.get("nombre", ""),
                email=request.form.get("email", ""),
                rol=request.form.get("rol", ""),
                password=request.form.get("password", ""),
                sueldo_diario=request.form.get("sueldo_diario", type=float) or 0,
            )
        except ErrorDeNegocio as error:
            db.session.rollback()
            flash(error.mensaje, "error")
        else:
            flash("Usuario creado correctamente.", "exito")
        return redirect(url_for("admin.usuarios"))

    return render_template(
        "admin/usuarios.html", usuarios=servicio.listar_usuarios(), roles=Rol.TODOS
    )


@admin_bp.route("/usuarios/<int:usuario_id>/editar", methods=["POST"])
@role_required(Rol.ADMIN)
def editar_usuario(usuario_id):
    try:
        _servicio().actualizar_usuario(
            usuario_id=usuario_id,
            nombre=request.form.get("nombre", ""),
            email=request.form.get("email", ""),
            rol=request.form.get("rol", ""),
            sueldo_diario=request.form.get("sueldo_diario", type=float) or 0,
            nueva_password=request.form.get("nueva_password") or None,
            activo=request.form.get("activo") == "on",
        )
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        flash("Datos del usuario actualizados.", "exito")
    return redirect(url_for("admin.usuarios"))


@admin_bp.route("/usuarios/<int:usuario_id>/estado", methods=["POST"])
@role_required(Rol.ADMIN)
def cambiar_estado(usuario_id):
    usuario = _servicio().obtener(usuario_id)
    if usuario is None:
        flash("El usuario indicado no existe.", "error")
        return redirect(url_for("admin.usuarios"))
    if usuario.id == g.usuario.id:
        flash("No puedes cambiar el estado de tu propia sesión.", "error")
        return redirect(url_for("admin.usuarios"))
    try:
        _servicio().cambiar_estado(usuario_id, not usuario.activo)
    except ErrorDeNegocio as error:
        db.session.rollback()
        flash(error.mensaje, "error")
    else:
        estado = "activado" if usuario.activo else "desactivado"
        flash(f"Usuario {estado} correctamente.", "exito")
    return redirect(url_for("admin.usuarios"))
