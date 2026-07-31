"""Authentication service backed by the central SQLite database."""

from medicus_privacy.modules.database import DatabaseService
from medicus_privacy.modules.roles import normalizar_rol
from medicus_privacy.modules.seguridad import (
    hash_password,
    password_necesita_actualizacion,
    verificar_password,
)


class AuthService:
    def __init__(self, db_path=None):
        self.database = DatabaseService(db_path)

    def verificar_credenciales(self, usuario, password):
        username = str(usuario or "").strip().lower()
        if not username or not isinstance(password, str):
            return False, None, None

        with self.database.connect() as connection:
            user = connection.execute(
                """
                SELECT id, username, password_hash, rol, nombre_completo, activo
                FROM usuarios
                WHERE username = ? COLLATE NOCASE
                """,
                (username,),
            ).fetchone()

            if not user or not user["activo"]:
                return False, None, None

            role = normalizar_rol(user["rol"])
            if not role or not verificar_password(password, user["password_hash"]):
                return False, None, None

            if password_necesita_actualizacion(user["password_hash"]):
                connection.execute(
                    "UPDATE usuarios SET password_hash = ? WHERE id = ?",
                    (hash_password(password), user["id"]),
                )

        user_data = {
            "user_id": user["id"],
            "nombre": user["nombre_completo"],
            "usuario": user["username"],
            "rol": role,
        }
        return True, role, user_data
