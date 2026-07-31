"""Compatibility entry point for the SQLite appointments module."""

import getpass

from medicus_privacy.modules.auth import AuthService
from medicus_privacy.modules.citas import CitasService, mostrar_menu_citas
from medicus_privacy.modules.database import DEFAULT_DB_PATH


DB_PATH = str(DEFAULT_DB_PATH)


if __name__ == "__main__":
    username = input("Usuario: ").strip()
    password = getpass.getpass("Contrasena: ")
    success, _, user_data = AuthService().verificar_credenciales(
        username,
        password,
    )
    if success:
        mostrar_menu_citas(user_data)
    else:
        print("Acceso denegado.")
