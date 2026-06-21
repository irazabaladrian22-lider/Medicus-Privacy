"""
Módulo de Administración (Estación 2) - Proyecto Medicus-Privacy
Gestiona la lista de empleados y sus roles en la base de datos (alta, baja y modificación).
"""

import json
import os
import sys

# Intentar importar el módulo de seguridad (Caja Fuerte)
# Soporta tanto una estructura plana en GitHub como la estructura local con carpetas
try:
    import seguridad
except ImportError:
    # Intentar agregando la carpeta SEGURIDAD al path
    ruta_seguridad = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'SEGURIDAD')
    if ruta_seguridad not in sys.path:
        sys.path.append(ruta_seguridad)
    try:
        import seguridad
    except ImportError:
        # Fallback simple si no se encuentra el módulo de seguridad
        seguridad = None

# Ruta de la base de datos JSON
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db_medicus.json')

# Lista de roles autorizados en el sistema
ROLES_PERMITIDOS = ["Admin", "Recep", "Médico", "Estudiante"]


def cargar_db() -> dict:
    """Carga los datos de db_medicus.json. Si no existe, crea una base con admin por defecto."""
    if not os.path.exists(DB_PATH):
        # Crear estructura base
        admin_pass_hash = ""
        if seguridad:
            admin_pass_hash = seguridad.hash_password("admin123")
        else:
            # Fallback si no hay modulo de seguridad
            admin_pass_hash = "admin123"
            
        db_inicial = {
            "usuarios": {
                "admin": {
                    "password_hash": admin_pass_hash,
                    "rol": "Admin",
                    "nombre_completo": "Administrador Principal"
                }
            },
            "citas": []
        }
        guardar_db(db_inicial)
        return db_inicial

    try:
        with open(DB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"\n[Error] No se pudo leer la base de datos: {e}")
        return {"usuarios": {}, "citas": []}


def guardar_db(datos: dict) -> bool:
    """Guarda los datos en db_medicus.json."""
    try:
        with open(DB_PATH, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"\n[Error] No se pudo escribir en la base de datos: {e}")
        return False


def crear_usuario(username: str, password_plain: str, rol: str, nombre_completo: str) -> tuple[bool, str]:
    """
    Registra un nuevo usuario en la base de datos con contraseña cifrada y rol asignado.
    
    Retorna:
        (bool, str): (Éxito, Mensaje informativo)
    """
    # Validaciones básicas
    username = username.strip().lower()
    nombre_completo = nombre_completo.strip()
    
    if not username or not password_plain or not nombre_completo:
        return False, "Todos los campos son obligatorios."
        
    if len(password_plain) < 4:
        return False, "La contraseña debe tener al menos 4 caracteres."
        
    if rol not in ROLES_PERMITIDOS:
        return False, f"Rol no permitido. Roles válidos: {', '.join(ROLES_PERMITIDOS)}"
        
    db = cargar_db()
    
    if username in db["usuarios"]:
        return False, f"El usuario '{username}' ya está registrado."
        
    # Cifrar contraseña usando el módulo seguridad
    if seguridad:
        password_hash = seguridad.hash_password(password_plain)
    else:
        password_hash = f"plain${password_plain}" # Fallback
        
    # Agregar usuario
    db["usuarios"][username] = {
        "password_hash": password_hash,
        "rol": rol,
        "nombre_completo": nombre_completo
    }
    
    if guardar_db(db):
        return True, f"Usuario '{username}' registrado exitosamente con rol '{rol}'."
    return False, "Error al guardar el usuario en la base de datos."


def eliminar_usuario(username: str) -> tuple[bool, str]:
    """
    Elimina a un usuario de la base de datos.
    No permite auto-eliminación si es el único administrador.
    
    Retorna:
        (bool, str): (Éxito, Mensaje informativo)
    """
    username = username.strip().lower()
    db = cargar_db()
    
    if username not in db["usuarios"]:
        return False, f"El usuario '{username}' no existe."
        
    # Evitar quedarse sin administradores
    usuario_a_eliminar = db["usuarios"][username]
    if usuario_a_eliminar["rol"] == "Admin":
        admins = [u for u, datos in db["usuarios"].items() if datos["rol"] == "Admin"]
        if len(admins) <= 1:
            return False, "Operación denegada: Debe existir al menos un usuario con rol 'Admin' en el sistema."
            
    # Eliminar usuario
    del db["usuarios"][username]
    
    if guardar_db(db):
        return True, f"Usuario '{username}' eliminado correctamente de la base de datos."
    return False, "Error al guardar los cambios en la base de datos."


def listar_usuarios() -> list[dict]:
    """Retorna una lista de usuarios registrados con sus datos básicos (sin contraseñas)."""
    db = cargar_db()
    lista = []
    for username, info in db["usuarios"].items():
        lista.append({
            "username": username,
            "rol": info["rol"],
            "nombre_completo": info["nombre_completo"]
        })
    return lista


def actualizar_rol_usuario(username: str, nuevo_rol: str) -> tuple[bool, str]:
    """Actualiza el rol de un usuario."""
    username = username.strip().lower()
    if nuevo_rol not in ROLES_PERMITIDOS:
        return False, f"Rol inválido. Debe ser uno de: {', '.join(ROLES_PERMITIDOS)}"
        
    db = cargar_db()
    if username not in db["usuarios"]:
        return False, f"El usuario '{username}' no existe."
        
    db["usuarios"][username]["rol"] = nuevo_rol
    if guardar_db(db):
        return True, f"Rol de '{username}' actualizado a '{nuevo_rol}'."
    return False, "Error al guardar cambios en la base de datos."


# --- INTERFAZ DE CONSOLA (MENU DE USUARIO) ---

def mostrar_menu_admin():
    """Muestra el panel de control interactivo de Administración."""
    while True:
        print("\n" + "=" * 50)
        print("    MEDICUS-PRIVACY - PANEL DE ADMINISTRACIÓN")
        print("=" * 50)
        print(" 1. Registrar Nuevo Usuario (Alta)")
        print(" 2. Eliminar Usuario (Baja)")
        print(" 3. Listar Todos los Usuarios")
        print(" 4. Cambiar Rol de un Usuario")
        print(" 5. Volver al Menú Principal / Salir")
        print("-" * 50)
        
        opcion = input("Seleccione una opción (1-5): ").strip()
        
        if opcion == "1":
            print("\n--- REGISTRAR NUEVO USUARIO ---")
            username = input("Nombre de usuario (ej. jgomez): ").strip()
            password = input("Contraseña temporal: ").strip()
            print("Roles disponibles:")
            for i, r in enumerate(ROLES_PERMITIDOS, 1):
                print(f"  {i}. {r}")
            try:
                rol_idx = int(input("Seleccione el rol (número): ").strip()) - 1
                if 0 <= rol_idx < len(ROLES_PERMITIDOS):
                    rol = ROLES_PERMITIDOS[rol_idx]
                else:
                    print("[!] Selección de rol inválida.")
                    continue
            except ValueError:
                print("[!] Entrada inválida. Debe ingresar un número.")
                continue
                
            nombre_completo = input("Nombre completo del empleado: ").strip()
            
            exito, mensaje = crear_usuario(username, password, rol, nombre_completo)
            if exito:
                print(f"\n[✔] {mensaje}")
            else:
                print(f"\n[✘] Error: {mensaje}")
                
        elif opcion == "2":
            print("\n--- ELIMINAR USUARIO ---")
            username = input("Ingrese el nombre de usuario a eliminar: ").strip()
            confirmacion = input(f"¿Está seguro de que desea eliminar a '{username}'? (s/n): ").strip().lower()
            if confirmacion == 's':
                exito, mensaje = eliminar_usuario(username)
                if exito:
                    print(f"\n[✔] {mensaje}")
                else:
                    print(f"\n[✘] Error: {mensaje}")
            else:
                print("\n[i] Operación cancelada.")
                
        elif opcion == "3":
            print("\n--- LISTA DE USUARIOS REGISTRADOS ---")
            usuarios = listar_usuarios()
            if not usuarios:
                print("No hay usuarios registrados.")
            else:
                print(f"{'Usuario':<15} | {'Rol':<12} | {'Nombre Completo'}")
                print("-" * 55)
                for u in usuarios:
                    print(f"{u['username']:<15} | {u['rol']:<12} | {u['nombre_completo']}")
                    
        elif opcion == "4":
            print("\n--- ACTUALIZAR ROL ---")
            username = input("Ingrese el nombre de usuario: ").strip()
            print("Roles disponibles:")
            for i, r in enumerate(ROLES_PERMITIDOS, 1):
                print(f"  {i}. {r}")
            try:
                rol_idx = int(input("Seleccione el nuevo rol (número): ").strip()) - 1
                if 0 <= rol_idx < len(ROLES_PERMITIDOS):
                    nuevo_rol = ROLES_PERMITIDOS[rol_idx]
                else:
                    print("[!] Selección de rol inválida.")
                    continue
            except ValueError:
                print("[!] Entrada inválida.")
                continue
                
            exito, mensaje = actualizar_rol_usuario(username, nuevo_rol)
            if exito:
                print(f"\n[✔] {mensaje}")
            else:
                print(f"\n[✘] Error: {mensaje}")
                
        elif opcion == "5":
            print("\nSaliendo del Panel de Administración...")
            break
        else:
            print("\n[!] Opción no válida. Intente de nuevo.")


if __name__ == "__main__":
    # Si se ejecuta directamente, simula la verificación básica antes de mostrar el menú
    print("=== MEDICUS-PRIVACY: Módulo admin.py ===")
    print("Para ingresar al menú de administración de forma autónoma, ingrese las credenciales del Admin.")
    
    user = input("Usuario: ").strip()
    pw = input("Contraseña: ").strip()
    
    db = cargar_db()
    if user in db["usuarios"] and db["usuarios"][user]["rol"] == "Admin":
        hash_stored = db["usuarios"][user]["password_hash"]
        
        # Validar contraseña
        acceso_concedido = False
        if seguridad:
            acceso_concedido = seguridad.verificar_password(pw, hash_stored)
        else:
            acceso_concedido = (hash_stored == f"plain${pw}" or hash_stored == pw)
            
        if acceso_concedido:
            print("\n[✔] Acceso concedido.")
            mostrar_menu_admin()
        else:
            print("\n[✘] Contraseña incorrecta.")
    else:
        print("\n[✘] Usuario no registrado o no tiene privilegios de administrador.")
