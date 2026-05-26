"""
Módulo Principal: Medicus-Privacy
Orquestador que integra autenticación, base de datos y gestión de citas médicas.
"""

import sys
import datetime
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ==============================================================================
# CONFIGURACIÓN GLOBAL
# ==============================================================================

# Nombre y versión de la aplicación
APP_NAME = "Medicus-Privacy"
APP_VERSION = "1.0.0"

# Carpeta donde se guardarán los archivos de log
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)  # Crea la carpeta si no existe

# Archivo de log completo
LOG_FILE = LOG_DIR / "medicus_audit.log"

# ==============================================================================
# SISTEMA DE LOGGING (Registro de eventos)
# ==============================================================================

def setup_logging():
    """
    Configura el sistema de registro de eventos.
    Los logs se guardan en archivos rotativos (máximo 10MB por archivo).
    """
    # Crea un logger con el nombre de la aplicación
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.INFO)  # Nivel INFO: registra eventos importantes
    
    # Rotación de logs: cuando llegue a 10MB, crea un archivo nuevo
    # backupCount=5 guarda los últimos 5 archivos de log
    handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    
    # Formato de cada línea de log: fecha | nivel | mensaje
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # También muestra los logs en consola para facilitar la depuración
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)  # En consola se ven todos los niveles
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    return logger

# Configura el logger al iniciar el módulo
logger = setup_logging()

# ==============================================================================
# IMPORTACIÓN DE MÓDULOS (Servicios reales o simulados)
# ==============================================================================

# Intenta importar los módulos reales del proyecto
try:
    from modules.auth import AuthService as RealAuth
    from modules.database import DatabaseService
    auth_service = RealAuth()
    logger.info("Módulos reales cargados correctamente")
    
except ImportError as e:
    # Si no están disponibles, usa versiones simuladas para desarrollo
    logger.warning(f"Módulos reales no encontrados. Usando simuladores (mocks). Error: {e}")
    
    # Simulador de autenticación para pruebas
    class MockAuth:
        @staticmethod
        def verificar_credenciales(usuario, password):
            """
            Verifica credenciales de acceso.
            Retorna: (éxito, rol, datos_usuario)
            """
            # Credenciales de prueba (solo para desarrollo)
            if usuario == "admin" and password == "admin123":
                return True, "Admin", {"user_id": 1, "nombre": "Admin Sistema"}
            if usuario == "medico" and password == "med123":
                return True, "Medico", {"user_id": 2, "nombre": "Dr. García"}
            if usuario == "paciente" and password == "pac123":
                return True, "Paciente", {"user_id": 3, "nombre": "María López"}
            
            # Credenciales incorrectas
            return False, None, None
    
    auth_service = MockAuth()

# ==============================================================================
# FUNCIONES AUXILIARES (Utilidades)
# ==============================================================================

def limpiar_pantalla():
    """Limpia la consola. Funciona en Windows (nt) y Linux/Mac."""
    os.system('cls' if os.name == 'nt' else 'clear')

def mostrar_banner():
    """Muestra el encabezado de la aplicación con nombre y versión."""
    limpiar_pantalla()
    print(f"""
    {'='*60}
    {APP_NAME} v{APP_VERSION}
    Sistema de Gestión de Citas Médicas con Privacidad por Diseño
    {'='*60}
    """)

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
            
            # En producción se usaría getpass para ocultar la contraseña
            # getpass.getpass("Contraseña: ")
            password = input("Contraseña: ")
            
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
                print(f"\n✅ Bienvenido, {nombre_usuario}")
                print(f"Rol asignado: {rol}")
                
                # Redirige al menú correspondiente según el rol
                if rol == "Admin":
                    print("🔧 Accediendo al panel de administración...")
                    # Aquí se llamaría: menu_administrador(datos_usuario)
                    
                elif rol == "Medico":
                    print("👨‍⚕️ Accediendo al panel médico...")
                    # Aquí se llamaría: menu_medico(datos_usuario)
                    
                else:
                    print("ℹ️ Accediendo al panel de paciente...")
                    # Aquí se llamaría: menu_paciente(datos_usuario)
                
                break  # Sale del bucle de login
                
            else:
                # Credenciales incorrectas
                intentos_fallidos += 1
                restantes = MAX_INTENTOS - intentos_fallidos
                
                # Registro de auditoría para intentos fallidos
                logger.warning(f"AUDITORIA | Acceso DENEGADO | Usuario: {usuario} | Intento {intentos_fallidos}/{MAX_INTENTOS}")
                
                print(f"\n❌ Usuario o contraseña incorrectos")
                print(f"Intentos restantes: {restantes}")
                
                # Si supera el máximo de intentos, cierra el sistema
                if intentos_fallidos >= MAX_INTENTOS:
                    logger.critical(f"SEGURIDAD | Usuario bloqueado temporalmente: {usuario} | Máximos intentos alcanzados")
                    print("\n🔒 Demasiados intentos fallidos. El sistema se cerrará por seguridad.")
                    input("Presione Enter para salir...")
                    sys.exit(1)  # Cierra el programa con código de error
        
    except KeyboardInterrupt:
        # El usuario presionó Ctrl+C
        logger.info("Sistema detenido manualmente por el usuario (Ctrl+C)")
        print("\n\n👋 Saliendo del sistema...")
        sys.exit(0)  # Cierra el programa normalmente
        
    except Exception as e:
        # Cualquier otro error inesperado
        logger.critical(f"Error fatal no manejado: {e}", exc_info=True)
        print(f"\n💥 Error crítico en el sistema. Contacte al administrador.")
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