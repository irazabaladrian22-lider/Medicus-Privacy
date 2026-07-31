"""Main CLI entry point for Medicus-Privacy."""

import getpass
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


APP_NAME = "Medicus-Privacy"
APP_VERSION = "2.0.0"
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "medicus_audit.log"


def setup_logging():
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


logger = setup_logging()

from medicus_privacy.modules.admin import mostrar_menu_admin
from medicus_privacy.modules.auth import AuthService
from medicus_privacy.modules.citas import mostrar_menu_citas
from medicus_privacy.modules.roles import ADMIN


def limpiar_pantalla():
    os.system("cls" if os.name == "nt" else "clear")


def mostrar_banner():
    limpiar_pantalla()
    print(
        f"\n{'=' * 60}\n"
        f"{APP_NAME} v{APP_VERSION}\n"
        "Sistema de Gestion de Citas Medicas con Privacidad\n"
        f"{'=' * 60}"
    )


def solicitar_password():
    try:
        return getpass.getpass("Contrasena (no se mostrara al escribir): ")
    except Exception:
        print("Esta consola no permite ocultar la contrasena.")
        return input("Contrasena: ")


def mostrar_panel(datos_usuario):
    if datos_usuario["rol"] != ADMIN:
        mostrar_menu_citas(datos_usuario)
        return

    while True:
        print("\n=== PANEL PRINCIPAL ADMIN ===")
        print("1. Administrar usuarios")
        print("2. Gestionar citas")
        print("0. Cerrar sesion")
        option = input("Seleccione una opcion: ").strip()
        if option == "1":
            mostrar_menu_admin(datos_usuario)
        elif option == "2":
            mostrar_menu_citas(datos_usuario)
        elif option == "0":
            return
        else:
            print("Opcion no valida.")


def main():
    mostrar_banner()
    logger.info("Inicio de %s v%s", APP_NAME, APP_VERSION)
    auth_service = AuthService()
    max_attempts = 3

    try:
        for attempt in range(1, max_attempts + 1):
            print("\n=== ACCESO AL SISTEMA ===")
            username = input("Usuario: ").strip()
            if not username:
                print("El nombre de usuario no puede estar vacio.")
                continue

            password = solicitar_password()
            success, role, user_data = auth_service.verificar_credenciales(
                username,
                password,
            )
            if success:
                logger.info(
                    "AUDITORIA | Acceso CONCEDIDO | Usuario: %s | Rol: %s | ID: %s",
                    username,
                    role,
                    user_data["user_id"],
                )
                print(f"\nBienvenido, {user_data['nombre']}")
                print(f"Rol asignado: {role}")
                mostrar_panel(user_data)
                return 0

            remaining = max_attempts - attempt
            logger.warning(
                "AUDITORIA | Acceso DENEGADO | Usuario: %s | Intento %s/%s",
                username,
                attempt,
                max_attempts,
            )
            print("Usuario o contrasena incorrectos.")
            print(f"Intentos restantes: {remaining}")

        logger.critical(
            "SEGURIDAD | Maximos intentos alcanzados | Usuario: %s",
            username,
        )
        return 1
    except KeyboardInterrupt:
        logger.info("Sistema detenido manualmente por el usuario.")
        print("\nSaliendo del sistema...")
        return 0
    except Exception:
        logger.exception("Error fatal no manejado")
        print("Error critico. Consulte el log de auditoria.")
        return 1
    finally:
        logger.info("El sistema ha finalizado su ejecucion")


if __name__ == "__main__":
    raise SystemExit(main())
