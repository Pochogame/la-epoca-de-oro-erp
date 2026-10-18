import re

from app.constants import Rol
from app.extensions import db
from app.repositories.usuario_repository import UsuarioRepositorio
from app.services.excepciones import AutenticacionError, DatosInvalidosError

PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PATRON_USERNAME = re.compile(r"^[a-z0-9._-]{3,30}$")


class AuthService:
    def __init__(self, usuarios=None):
        self.usuarios = usuarios or UsuarioRepositorio()

    def autenticar(self, username, password):
        if not username or not password:
            raise AutenticacionError("Captura tu usuario y contraseña.")
        usuario = self.usuarios.por_username(username)
        if usuario is None or not usuario.verificar_password(password):
            raise AutenticacionError("Usuario o contraseña incorrectos.")
        if not usuario.activo:
            raise AutenticacionError("Tu cuenta está desactivada. Contacta al administrador.")
        return usuario

    def _validar_password(self, password):
        if not password or len(password) < 6:
            raise DatosInvalidosError("La contraseña debe tener al menos 6 caracteres.")

    def restablecer_password(self, username, email, nueva_password):
        usuario = self.usuarios.por_username(username or "")
        if usuario is None or usuario.email.lower() != (email or "").strip().lower():
            raise AutenticacionError(
                "El usuario y el correo no coinciden con nuestros registros."
            )
        self._validar_password(nueva_password)
        usuario.definir_password(nueva_password)
        db.session.commit()
        return usuario

    def crear_usuario(self, username, nombre, email, rol, password, sueldo_diario=0.0):
        username = (username or "").strip().lower()
        nombre = (nombre or "").strip()
        email = (email or "").strip().lower()

        if not username or not nombre or not email:
            raise DatosInvalidosError("Usuario, nombre y correo son obligatorios.")
        if not PATRON_USERNAME.match(username):
            raise DatosInvalidosError(
                "El usuario debe tener entre 3 y 30 caracteres (letras, números, punto, guion)."
            )
        if not PATRON_EMAIL.match(email):
            raise DatosInvalidosError("El correo electrónico no tiene un formato válido.")
        if rol not in Rol.TODOS:
            raise DatosInvalidosError("El rol seleccionado no es válido.")
        self._validar_password(password)
        if self.usuarios.por_username(username):
            raise DatosInvalidosError(f"El usuario '{username}' ya existe.")
        if self.usuarios.por_email(email):
            raise DatosInvalidosError(f"El correo '{email}' ya está registrado.")

        from app.models.usuario import Usuario

        usuario = Usuario(
            username=username,
            nombre=nombre,
            email=email,
            rol=rol,
            sueldo_diario=max(float(sueldo_diario or 0), 0),
        )
        usuario.definir_password(password)
        self.usuarios.agregar(usuario)
        db.session.commit()
        return usuario

    def actualizar_usuario(
        self, usuario_id, nombre, email, rol, sueldo_diario, nueva_password=None, activo=None
    ):
        usuario = self.usuarios.obtener(usuario_id)
        if usuario is None:
            raise DatosInvalidosError("El usuario indicado no existe.")
        nombre = (nombre or "").strip()
        email = (email or "").strip().lower()
        if not nombre or not email:
            raise DatosInvalidosError("Nombre y correo son obligatorios.")
        if not PATRON_EMAIL.match(email):
            raise DatosInvalidosError("El correo electrónico no tiene un formato válido.")
        if rol not in Rol.TODOS:
            raise DatosInvalidosError("El rol seleccionado no es válido.")
        existente = self.usuarios.por_email(email)
        if existente is not None and existente.id != usuario.id:
            raise DatosInvalidosError(f"El correo '{email}' ya está registrado por otro usuario.")

        usuario.nombre = nombre
        usuario.email = email
        usuario.rol = rol
        usuario.sueldo_diario = max(float(sueldo_diario or 0), 0)
        if activo is not None:
            usuario.activo = bool(activo)
        if nueva_password:
            self._validar_password(nueva_password)
            usuario.definir_password(nueva_password)
        db.session.commit()
        return usuario

    def cambiar_estado(self, usuario_id, activo):
        usuario = self.usuarios.obtener(usuario_id)
        if usuario is None:
            raise DatosInvalidosError("El usuario indicado no existe.")
        if usuario.es_admin and not activo:
            otros_admins = [
                u for u in self.usuarios.activos() if u.es_admin and u.id != usuario.id
            ]
            if not otros_admins:
                raise DatosInvalidosError(
                    "No puedes desactivar al último administrador activo del sistema."
                )
        usuario.activo = bool(activo)
        db.session.commit()
        return usuario

    def listar_usuarios(self):
        return self.usuarios.todos_ordenados()

    def obtener(self, usuario_id):
        return self.usuarios.obtener(usuario_id)
