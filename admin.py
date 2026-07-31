"""Compatibility entry point for SQLite user administration."""

import getpass

from medicus_privacy.modules.admin import AdminService, mostrar_menu_admin
from medicus_privacy.modules.auth import AuthService
from medicus_privacy.modules.database import DEFAULT_DB_PATH
from medicus_privacy.modules.roles import ADMIN, ROLES_PERMITIDOS


DB_PATH = str(DEFAULT_DB_PATH)


def crear_usuario(
    username,
    password_plain,
    rol,
    nombre_completo,
    especialidad=None,
):
    return AdminService(ADMIN).crear_usuario(
        username,
        password_plain,
        rol,
        nombre_completo,
        especialidad,
    )


def eliminar_usuario(username):
    return AdminService(ADMIN).eliminar_usuario(username)


def listar_usuarios():
    return AdminService(ADMIN).listar_usuarios()


def actualizar_usuario(username, nombre_completo, rol, especialidad=None):
    return AdminService(ADMIN).actualizar_usuario(
        username,
        nombre_completo,
        rol,
        especialidad,
    )


def actualizar_rol_usuario(username, nuevo_rol):
    return AdminService(ADMIN).actualizar_rol_usuario(username, nuevo_rol)


if __name__ == "__main__":
    username = input("Usuario administrador: ").strip()
    password = getpass.getpass("Contrasena: ")
    success, role, user_data = AuthService().verificar_credenciales(
        username,
        password,
    )
    if success and role == ADMIN:
        mostrar_menu_admin(user_data)
    else:
        print("Acceso denegado.")
