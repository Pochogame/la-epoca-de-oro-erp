import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "la-epoca-de-oro-clave-desarrollo")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'instance' / 'la_epoca_de_oro.db').as_posix()}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_CREAR_BD = True
    AUTO_SEMBRAR = True


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "clave-de-pruebas"
    SQLALCHEMY_DATABASE_URI = "sqlite://"


def get_config(nombre=None):
    if nombre == "testing":
        return TestingConfig
    return Config
