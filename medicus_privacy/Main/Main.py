"""
Modulo Principal: Medicus-Privacy
Orquestador que integra autenticaciÃ³n, base de datos y gestiÃ³n de citas mÃ©dicas.
"""

import sys
import os
import logging
import getpass
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ==============================================================================
# CONFIGURACION GLOBAL
# ==============================================================================

# Nombre y version de la aplicacion
APP_NAME = "Medicus-Privacy"
APP_VERSION = "1.0.0"

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Carpeta donde se guardaran los archivos de log
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)  # Crea la carpeta si no existe

# Archivo de log completo
LOG_FILE = LOG_DIR / "medicus_audit.log"

# ==============================================================================
# SISTEMA DE LOGGING (Registro de eventos)
# ==============================================================================

def setup_logging():
    """
    Configura el sistema de registro de eventos.
    Los logs se guardan en archivos rotativos (mÃ¡ximo 10MB por archivo).
    """
    # Crea un logger con el nombre de la aplicaciÃ³n
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.INFO)  # Nivel INFO: registra eventos importantes
    if logger.handlers:
        return logger
    
    # Rotacion de logs: cuando llegue a 10MB, crea un archivo nuevo
    # backupCount=5 guarda los Ãºltimos 5 archivos de log
    handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    
    # Formato de cada linea de log: fecha | nivel | mensaje
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Tambien muestra los logs en consola para facilitar la depuracion
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)  # En consola se ven todos los niveles
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    return logger

# Configura el logger al iniciar el modulo
logger = setup_logging()

# ==============================================================================
# IMPORTACION DE MODULOS (Servicios reales o simulados)
# ==============================================================================

# Intenta importar los modulos reales del proyecto
try:
    from medicus_privacy.modules.auth import AuthService

    auth_service = AuthService()
    logger.info("Modulo de autenticacion cargado correctamente")
except ImportError as e:
    logger.critical(f"No se pudo cargar el modulo de autenticacion: {e}")
    raise
except Exception as e:
    logger.critical(f"Error configurando autenticacion: {e}", exc_info=True)
    raise


# ==============================================================================
# FUNCIONES AUXILIARES (Utilidades)
# ==============================================================================

def limpiar_pantalla():
    os.system('cls' if os.name == 'nt' else 'clear')

def mostrar_banner():
    """Muestra el encabezado de la aplicacion con nombre y version."""
    limpiar_pantalla()
    print(f"""
    {'='*60}
    {APP_NAME} v{APP_VERSION}
    Sistema de Gestion de Citas Medicas con Privacidad
    {'='*60}
    """)


def solicitar_password():
    """Solicita la contrasena de forma oculta, con fallback para consolas limitadas."""
    try:
        return getpass.getpass("Contrasena (no se mostrara al escribir): ")
    except Exception:
        print("Aviso: esta consola no permite ocultar la contrasena.")
        return input("Contrasena: ")

# ==============================================================================
# FLUJO PRINCIPAL DEL PROGRAMA
# ==============================================================================

def main():
    """
    Punto de entrada principal del sistema.
    Maneja el login y redirige según el rol del usuario.
    """
    try:
        # Muestra el banner de bienvenida
        mostrar_banner()
        logger.info(f"Inicio de {APP_NAME} v{APP_VERSION}")
        
        # Control de intentos fallidos por seguridad
        intentos_fallidos = 0
        MAX_INTENTOS = 3  # Máximo de intentos antes de cerrar el sistema
        
        # Bucle principal de autenticación
        while intentos_fallidos < MAX_INTENTOS:
            print("\n=== ACCESO AL SISTEMA ===")
            usuario = input("Usuario: ").strip()  # .strip() elimina espacios en blanco
            
            password = solicitar_password()
            
            # Validación básica: el usuario no puede estar vacío
            if not usuario:
                print("Error: El nombre de usuario no puede estar vacío")
                continue  # Vuelve al inicio del bucle
            
            # Intenta autenticar al usuario
            exito, rol, datos_usuario = auth_service.verificar_credenciales(usuario, password)
            
            if exito:
                # Registro de auditoría para accesos exitosos
                logger.info(f"AUDITORIA | Acceso CONCEDIDO | Usuario: {usuario} | Rol: {rol} | ID: {datos_usuario.get('user_id')}")
                
                # Muestra mensaje de bienvenida personalizado
                nombre_usuario = datos_usuario.get('nombre', usuario)
                print(f"\n Bienvenido, {nombre_usuario}")
                print(f"Rol asignado: {rol}")
                
                # Redirige al menú correspondiente según el rol
                if rol == "Admin":
                    print("Accediendo al panel de administración...")
                    # Aquí se llamaría: menu_administrador(datos_usuario)
                    
                elif rol == "Medico":
                    print(" Accediendo al panel médico...")
                    # Aquí se llamaría: menu_medico(datos_usuario)

                elif rol == "Recepcionista":
                    print("Accediendo al panel de recepcion...")
                    # Aquí se llamaría: menu_recepcionista(datos_usuario)

                elif rol == "Estudiante":
                    print("Accediendo al panel de estudiante...")
                    # Aquí se llamaría: menu_estudiante(datos_usuario)
                    
                else:
                    logger.error(f"Rol autenticado sin menu asignado: {rol}")
                    print("Error: rol sin menu asignado. Contacte al administrador.")
                
                break  # Sale del bucle de login
                
            else:
                # Credenciales incorrectas
                intentos_fallidos += 1
                restantes = MAX_INTENTOS - intentos_fallidos
                
                # Registro de auditoría para intentos fallidos
                logger.warning(f"AUDITORIA | Acceso DENEGADO | Usuario: {usuario} | Intento {intentos_fallidos}/{MAX_INTENTOS}")
                
                print(f"\n Usuario o contraseña incorrectos")
                print(f"Intentos restantes: {restantes}")
                
                # Si supera el mÃ¡ximo de intentos, cierra el sistema
                if intentos_fallidos >= MAX_INTENTOS:
                    logger.critical(f"SEGURIDAD | Usuario bloqueado temporalmente: {usuario} | Maximos intentos alcanzados")
                    print("\n Demasiados intentos fallidos. El sistema se cerrara¡ por seguridad.")
                    input("Presione Enter para salir...")
                    sys.exit(1)  # Cierra el programa con cÃ³digo de error
        
    except KeyboardInterrupt:
        # El usuario presionaddd Ctrl+C
        logger.info("Sistema detenido manualmente por el usuario (Ctrl+C)")
        print("\n\n Saliendo del sistema...")
        sys.exit(0)  # Cierra el programa normalmente
        
    except Exception as e:
        # Cualquier otro error inesperado
        logger.critical(f"Error fatal no manejado: {e}", exc_info=True)
        print(f"\n Error crítico en el sistema. Contacte al administrador.")
        print(f"Código de referencia: {type(e).__name__}")
        sys.exit(1)  # Cierra con código de error
        
    finally:
        # Este bloque se ejecuta siempre, haya error o no
        logger.info("El sistema ha finalizado su ejecución")

# ==============================================================================
# PUNTO DE ENTRADA
# ==============================================================================

# Esta condición verifica que el script se ejecute directamente
# (no cuando se importe como módulo desde otro archivo)
if __name__ == "__main__":
    main()
