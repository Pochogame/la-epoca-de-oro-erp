from functools import wraps

from flask import abort, g, redirect, url_for, session

from app.extensions import db
from app.models.usuario import Usuario


def cargar_usuario_actual():
    usuario_id = session.get("usuario_id")
    g.usuario = db.session.get(Usuario, usuario_id) if usuario_id else None
    if g.usuario is not None and not g.usuario.activo:
        session.clear()
        g.usuario = None


def registrar_seguridad(app):
    app.before_request(cargar_usuario_actual)


def login_required(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if g.usuario is None:
            return redirect(url_for("auth.login"))
        return vista(*args, **kwargs)

    return envoltura


def role_required(*roles):
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if g.usuario is None:
                return redirect(url_for("auth.login"))
            if g.usuario.rol not in roles:
                abort(403)
            return vista(*args, **kwargs)

        return envoltura

    return decorador
