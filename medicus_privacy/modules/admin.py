"""User administration with clinical specialty validation."""

import re
import sqlite3

from medicus_privacy.modules.catalogs import normalize_specialty
from medicus_privacy.modules.database import DatabaseService
from medicus_privacy.modules.roles import (
    ADMIN,
    ESTUDIANTE,
    MEDICO,
    ROLES_PERMITIDOS,
    normalizar_rol,
)
from medicus_privacy.modules.seguridad import hash_password


USERNAME_PATTERN = re.compile(r"^[a-z0-9_.-]{3,32}$")
MIN_PASSWORD_LENGTH = 8
CLINICAL_ROLES = (MEDICO, ESTUDIANTE)


class AdminService:
    def __init__(self, actor_role, db_path=None):
        self.actor_role = normalizar_rol(actor_role)
        self.database = DatabaseService(db_path)

    def _authorized(self):
        return self.actor_role == ADMIN

    @staticmethod
    def _profile_values(role, specialty):
        if role in CLINICAL_ROLES:
            normalized = normalize_specialty(specialty)
            if not normalized:
                return None, "Seleccione una especialidad valida."
            return normalized, None
        return None, None

    def crear_usuario(
        self,
        username,
        password,
        rol,
        nombre_completo,
        especialidad=None,
    ):
        if not self._authorized():
            return False, "Operacion permitida solo para administradores."

        username = str(username or "").strip().lower()
        name = str(nombre_completo or "").strip()
        role = normalizar_rol(rol)
        if not USERNAME_PATTERN.fullmatch(username):
            return (
                False,
                "El usuario debe tener entre 3 y 32 caracteres: letras, numeros, "
                "punto, guion o guion bajo.",
            )
        if not name:
            return False, "El nombre completo es obligatorio."
        if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
            return False, "La contrasena debe tener al menos 8 caracteres."
        if role not in ROLES_PERMITIDOS:
            return False, f"Rol no permitido: {rol}."
        specialty, error = self._profile_values(role, especialidad)
        if error:
            return False, error

        try:
            with self.database.connect() as connection:
                connection.execute(
                    """
                    INSERT INTO usuarios (
                        username, password_hash, rol, nombre_completo,
                        especialidad, activo
                    ) VALUES (?, ?, ?, ?, ?, 1)
                    """,
                    (username, hash_password(password), role, name, specialty),
                )
            return True, f"Usuario '{username}' registrado con rol '{role}'."
        except sqlite3.IntegrityError:
            return False, f"El usuario '{username}' ya existe."

    def actualizar_usuario(
        self,
        username,
        nombre_completo,
        rol,
        especialidad=None,
    ):
        if not self._authorized():
            return False, "Operacion permitida solo para administradores."

        username = str(username or "").strip().lower()
        name = str(nombre_completo or "").strip()
        role = normalizar_rol(rol)
        if not name:
            return False, "El nombre completo es obligatorio."
        if role not in ROLES_PERMITIDOS:
            return False, f"Rol no permitido: {rol}."
        specialty, error = self._profile_values(role, especialidad)
        if error:
            return False, error

        with self.database.connect() as connection:
            user = connection.execute(
                "SELECT id, rol, activo FROM usuarios WHERE username = ?",
                (username,),
            ).fetchone()
            if not user:
                return False, f"El usuario '{username}' no existe."
            if (
                user["rol"] == ADMIN
                and role != ADMIN
                and user["activo"]
                and self._active_admin_count(connection) <= 1
            ):
                return False, "No se puede cambiar el rol del unico administrador."
            connection.execute(
                """
                UPDATE usuarios
                SET nombre_completo = ?, rol = ?, especialidad = ?
                WHERE id = ?
                """,
                (name, role, specialty, user["id"]),
            )
        return True, f"Usuario '{username}' actualizado correctamente."

    def actualizar_rol_usuario(self, username, nuevo_rol):
        users = {
            user["username"]: user
            for user in self.listar_usuarios(incluir_inactivos=True)
        }
        user = users.get(str(username or "").strip().lower())
        if not user:
            return False, f"El usuario '{username}' no existe."
        return self.actualizar_usuario(
            user["username"],
            user["nombre_completo"],
            nuevo_rol,
            user["especialidad"],
        )

    def eliminar_usuario(self, username):
        if not self._authorized():
            return False, "Operacion permitida solo para administradores."
        username = str(username or "").strip().lower()
        with self.database.connect() as connection:
            user = connection.execute(
                "SELECT id, rol, activo FROM usuarios WHERE username = ?",
                (username,),
            ).fetchone()
            if not user or not user["activo"]:
                return False, f"El usuario '{username}' no existe o ya esta inactivo."
            if user["rol"] == ADMIN and self._active_admin_count(connection) <= 1:
                return False, "Debe existir al menos un administrador activo."
            connection.execute(
                "UPDATE usuarios SET activo = 0 WHERE id = ?",
                (user["id"],),
            )
        return True, f"Usuario '{username}' desactivado correctamente."

    def activar_usuario(self, username):
        if not self._authorized():
            return False, "Operacion permitida solo para administradores."
        username = str(username or "").strip().lower()
        with self.database.connect() as connection:
            result = connection.execute(
                "UPDATE usuarios SET activo = 1 WHERE username = ? AND activo = 0",
                (username,),
            )
            if result.rowcount == 0:
                return False, f"El usuario '{username}' no existe o ya esta activo."
        return True, f"Usuario '{username}' activado correctamente."

    def listar_usuarios(self, incluir_inactivos=False):
        if not self._authorized():
            return []
        where = "" if incluir_inactivos else "WHERE activo = 1"
        with self.database.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT id, username, rol, nombre_completo, especialidad, activo
                FROM usuarios
                {where}
                ORDER BY username
                """
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _active_admin_count(connection):
        return connection.execute(
            "SELECT COUNT(*) FROM usuarios WHERE rol = ? AND activo = 1",
            (ADMIN,),
        ).fetchone()[0]


def mostrar_menu_admin(datos_usuario, db_path=None):
    service = AdminService(datos_usuario.get("rol"), db_path)
    if not service._authorized():
        print("Acceso denegado: se requiere rol Admin.")
        return
    print("La administracion completa de usuarios esta disponible en la GUI.")
