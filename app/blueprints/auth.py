from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from app.services.auth_service import AuthService
from app.services.excepciones import ErrorDeNegocio

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.usuario is not None:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        try:
            usuario = AuthService().autenticar(
                request.form.get("username", ""), request.form.get("password", "")
            )
        except ErrorDeNegocio as error:
            flash(error.mensaje, "error")
        else:
            session.clear()
            session["usuario_id"] = usuario.id
            flash(f"¡Bienvenido(a), {usuario.nombre}!", "exito")
            return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "exito")
    return redirect(url_for("auth.login"))


@auth_bp.route("/recuperar-password", methods=["GET", "POST"])
def recuperar_password():
    if request.method == "POST":
        try:
            usuario = AuthService().restablecer_password(
                request.form.get("username", ""),
                request.form.get("email", ""),
                request.form.get("password", ""),
            )
        except ErrorDeNegocio as error:
            flash(error.mensaje, "error")
        else:
            flash(
                f"Contraseña actualizada para '{usuario.username}'. Ya puedes iniciar sesión.",
                "exito",
            )
            return redirect(url_for("auth.login"))
    return render_template("auth/recuperar.html")
