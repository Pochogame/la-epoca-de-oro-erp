import os

from flask import Flask

from app.config import get_config
from app.constants import (
    CATEGORIAS_GASTO,
    GUISADOS,
    MOTIVOS_MERMA,
    EstadoAsistencia,
    EstadoComanda,
    EstadoPago,
    MetodoPago,
    Rol,
    TipoMovimiento,
    TipoOrden,
    Turno,
)
from app.extensions import db
from app.security import registrar_seguridad


def create_app(nombre_config=None):
    app = Flask(__name__)
    app.config.from_object(get_config(nombre_config))
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    registrar_seguridad(app)
    _registrar_filtros(app)
    _registrar_contexto(app)
    _registrar_blueprints(app)
    _registrar_manejadores_de_error(app)
    _preparar_base_de_datos(app)
    return app


def _registrar_filtros(app):
    @app.template_filter("moneda")
    def moneda(valor):
        try:
            return f"${float(valor or 0):,.2f}"
        except (TypeError, ValueError):
            return "$0.00"

    @app.template_filter("cantidad")
    def cantidad(valor):
        try:
            return f"{float(valor or 0):g}"
        except (TypeError, ValueError):
            return "0"

    @app.template_filter("fecha_corta")
    def fecha_corta(valor):
        return valor.strftime("%d/%m/%Y") if valor else ""

    @app.template_filter("fecha_hora")
    def fecha_hora(valor):
        return valor.strftime("%d/%m/%Y %H:%M") if valor else ""

    @app.template_filter("hora")
    def hora(valor):
        return valor.strftime("%H:%M") if valor else "--:--"


def _registrar_contexto(app):
    from datetime import datetime

    @app.context_processor
    def inyectar_constantes():
        return {
            "now": datetime.now(),
            "Rol": Rol,
            "Turno": Turno,
            "TipoOrden": TipoOrden,
            "MetodoPago": MetodoPago,
            "EstadoComanda": EstadoComanda,
            "EstadoPago": EstadoPago,
            "EstadoAsistencia": EstadoAsistencia,
            "TipoMovimiento": TipoMovimiento,
            "CATEGORIAS_GASTO": CATEGORIAS_GASTO,
            "MOTIVOS_MERMA": MOTIVOS_MERMA,
            "GUISADOS": GUISADOS,
        }


def _registrar_blueprints(app):
    from app.blueprints.admin import admin_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.cocina import cocina_bp
    from app.blueprints.contabilidad import contabilidad_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.inventario import inventario_bp
    from app.blueprints.pos import pos_bp
    from app.blueprints.recetas import recetas_bp
    from app.blueprints.rrhh import rrhh_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(pos_bp)
    app.register_blueprint(cocina_bp)
    app.register_blueprint(inventario_bp)
    app.register_blueprint(recetas_bp)
    app.register_blueprint(contabilidad_bp)
    app.register_blueprint(rrhh_bp)
    app.register_blueprint(admin_bp)


def _registrar_manejadores_de_error(app):
    from flask import render_template

    @app.errorhandler(403)
    def sin_permiso(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def no_encontrado(_error):
        return render_template("errors/404.html"), 404


def _preparar_base_de_datos(app):
    with app.app_context():
        if app.config.get("AUTO_CREAR_BD"):
            db.create_all()
        if app.config.get("AUTO_SEMBRAR"):
            from app.seed import seed_database

            seed_database()
