"""
Módulo de Citas/Reservas (Estación 3) - Proyecto Medicus-Privacy
Gestiona la agenda, la disponibilidad de los médicos y el registro de citas de alumnos.
Integra cifrado de motivos de consulta médicos para proteger datos confidenciales.
"""

import json
import os
import sys
import re

# Intentar importar el módulo de seguridad (Caja Fuerte)
try:
    import seguridad
except ImportError:
    ruta_seguridad = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'SEGURIDAD')
    if ruta_seguridad not in sys.path:
        sys.path.append(ruta_seguridad)
    try:
        import seguridad
    except ImportError:
        seguridad = None

# Ruta de la base de datos JSON
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db_medicus.json')


def cargar_db() -> dict:
    """Carga los datos de db_medicus.json."""
    if not os.path.exists(DB_PATH):
        # Crear estructura base si no existe
        db_inicial = {"usuarios": {}, "citas": []}
        try:
            with open(DB_PATH, 'w', encoding='utf-8') as f:
                json.dump(db_inicial, f, indent=2)
            return db_inicial
        except Exception:
            return {"usuarios": {}, "citas": []}

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


def validar_fecha(fecha: str) -> bool:
    """Valida formato AAAA-MM-DD."""
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", fecha))


def validar_hora(hora: str) -> bool:
    """Valida formato HH:MM (24 horas)."""
    return bool(re.match(r"^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$", hora))


def verificar_disponibilidad(medico_username: str, fecha: str, hora: str) -> bool:
    """
    Verifica si el médico está disponible en una fecha y hora específicas.
    Retorna True si está libre, False si ya tiene una cita asignada.
    """
    db = cargar_db()
    for cita in db["citas"]:
        if (cita["medico"].lower() == medico_username.lower() and 
            cita["fecha"] == fecha and 
            cita["hora"] == hora and
            cita.get("estado", "Programada") != "Cancelada"):
            return False
    return True


def agendar_cita(medico_username: str, alumno_username: str, fecha: str, hora: str, 
                 especialidad: str, motivo_sensible: str = "", clave_seguridad: str = None) -> tuple[bool, str]:
    """
    Registra una cita en la agenda verificando la existencia de los usuarios, sus roles y la disponibilidad.
    Si se proporciona un motivo_sensible y una clave_seguridad, el motivo es cifrado antes de guardarlo.
    
    Retorna:
        (bool, str): (Éxito, Mensaje informativo)
    """
    medico_username = medico_username.strip().lower()
    alumno_username = alumno_username.strip().lower()
    fecha = fecha.strip()
    hora = hora.strip()
    especialidad = especialidad.strip()
    motivo_sensible = motivo_sensible.strip()
    
    if not medico_username or not alumno_username or not fecha or not hora or not especialidad:
        return False, "Los campos médico, alumno, fecha, hora y especialidad son obligatorios."
        
    if not validar_fecha(fecha):
        return False, "La fecha debe tener el formato AAAA-MM-DD."
        
    if not validar_hora(hora):
        return False, "La hora debe tener el formato HH:MM (24 horas, ej: 14:30)."
        
    db = cargar_db()
    
    # Validar que el médico exista y tenga rol Médico
    if medico_username not in db["usuarios"]:
        return False, f"El médico '{medico_username}' no existe en el sistema."
    if db["usuarios"][medico_username]["rol"] != "Médico":
        return False, f"El usuario '{medico_username}' no tiene rol de 'Médico'."
        
    # Validar que el alumno exista
    if alumno_username not in db["usuarios"]:
        return False, f"El alumno '{alumno_username}' no existe en el sistema."
    if db["usuarios"][alumno_username]["rol"] != "Estudiante":
        return False, f"El usuario '{alumno_username}' no es un 'Estudiante'."
        
    # Validar disponibilidad del médico
    if not verificar_disponibilidad(medico_username, fecha, hora):
        return False, f"El médico '{medico_username}' no está disponible el {fecha} a las {hora}."
        
    # Procesar cifrado del motivo de consulta si hay módulo de seguridad y clave provista
    motivo_guardar = motivo_sensible
    cifrado_activo = False
    
    if motivo_sensible:
        if clave_seguridad and seguridad:
            try:
                motivo_guardar = seguridad.cifrar_datos(motivo_sensible, clave_seguridad)
                cifrado_activo = True
            except Exception as e:
                return False, f"Error al cifrar los datos de la cita: {e}"
        elif motivo_sensible and not clave_seguridad:
            return False, "Para registrar datos médicos confidenciales (motivo), se requiere una clave de seguridad de cifrado."
            
    # Generar un ID incremental
    id_cita = str(len(db["citas"]) + 1)
    
    nueva_cita = {
        "id": id_cita,
        "medico": medico_username,
        "alumno": alumno_username,
        "fecha": fecha,
        "hora": hora,
        "especialidad": especialidad,
        "motivo": motivo_guardar,
        "cifrado": cifrado_activo,
        "estado": "Programada"
    }
    
    db["citas"].append(nueva_cita)
    
    if guardar_db(db):
        msg = f"Cita ID {id_cita} agendada correctamente."
        if cifrado_activo:
            msg += " (Motivo médico protegido con cifrado de seguridad)"
        return True, msg
    return False, "Error al escribir en la base de datos."


def cancelar_cita(cita_id: str) -> tuple[bool, str]:
    """Cancela una cita médica cambiando su estado a 'Cancelada'."""
    cita_id = cita_id.strip()
    db = cargar_db()
    
    for cita in db["citas"]:
        if cita["id"] == cita_id:
            if cita.get("estado") == "Cancelada":
                return False, "La cita ya se encuentra cancelada."
            cita["estado"] = "Cancelada"
            if guardar_db(db):
                return True, f"La cita ID {cita_id} ha sido cancelada con éxito."
            return False, "Error al guardar el estado en la base de datos."
            
    return False, f"No se encontró la cita con el ID {cita_id}."


def obtener_citas_filtradas(rol_usuario: str, username: str) -> list[dict]:
    """Retorna la lista de citas correspondientes a los permisos de un usuario."""
    db = cargar_db()
    rol_usuario = rol_usuario.strip()
    username = username.strip().lower()
    
    citas_retorno = []
    
    for cita in db["citas"]:
        if rol_usuario in ["Admin", "Recep"]:
            # Ven todas las citas
            citas_retorno.append(cita)
        elif rol_usuario == "Médico" and cita["medico"].lower() == username:
            # Ve solo las de su consultorio
            citas_retorno.append(cita)
        elif rol_usuario == "Estudiante" and cita["alumno"].lower() == username:
            # Ve solo sus propias citas
            citas_retorno.append(cita)
            
    return citas_retorno


def descifrar_motivo_cita(cita: dict, clave_seguridad: str) -> str:
    """Intenta descifrar el motivo de una cita. Retorna el texto plano o mensaje de error."""
    if not cita.get("cifrado"):
        return cita.get("motivo", "")
        
    if not seguridad:
        return "[Error: Módulo de seguridad no disponible]"
        
    if not clave_seguridad:
        return "[DATO CIFRADO - Requiere Clave]"
        
    try:
        texto_descifrado = seguridad.descifrar_datos(cita["motivo"], clave_seguridad)
        return texto_descifrado
    except ValueError:
        return "[DATO CIFRADO - Clave Incorrecta o Alterado]"
    except Exception as e:
        return f"[DATO CIFRADO - Error de descifrado: {e}]"


# --- INTERFAZ DE CONSOLA (MENU DE RESERVAS) ---

def mostrar_menu_citas(username_actual: str, rol_actual: str):
    """Muestra el panel de la agenda y reservas adaptado al rol del usuario."""
    db = cargar_db()
    
    while True:
        print("\n" + "=" * 60)
        print(f"   MEDICUS-PRIVACY - GESTIÓN DE CITAS ({rol_actual}: {username_actual})")
        print("=" * 60)
        
        # Opciones adaptadas según el rol
        if rol_actual in ["Admin", "Recep"]:
            print(" 1. Agendar Nueva Cita")
            print(" 2. Cancelar Cita Médica")
            print(" 3. Listar Todas las Citas (Motivos de consulta cifrados)")
            print(" 4. Volver al Menú Principal / Salir")
            print("-" * 60)
            opcion = input("Seleccione una opción (1-4): ").strip()
            
            if opcion == "1":
                print("\n--- AGENDAR NUEVA CITA ---")
                medico = input("Nombre de usuario del Médico: ").strip()
                alumno = input("Nombre de usuario del Estudiante: ").strip()
                fecha = input("Fecha (AAAA-MM-DD): ").strip()
                hora = input("Hora (HH:MM): ").strip()
                especialidad = input("Especialidad médica (ej. Odontología): ").strip()
                motivo = input("Motivo de consulta (opcional, confidencial): ").strip()
                
                clave = None
                if motivo:
                    clave = input("Ingrese clave de seguridad para proteger este diagnóstico: ").strip()
                    
                exito, mensaje = agendar_cita(medico, alumno, fecha, hora, especialidad, motivo, clave)
                if exito:
                    print(f"\n[✔] {mensaje}")
                else:
                    print(f"\n[✘] Error: {mensaje}")
                    
            elif opcion == "2":
                print("\n--- CANCELAR CITA MÉDICA ---")
                cita_id = input("Ingrese el ID de la cita a cancelar: ").strip()
                confirmacion = input(f"¿Está seguro de cancelar la cita ID {cita_id}? (s/n): ").strip().lower()
                if confirmacion == 's':
                    exito, mensaje = cancelar_cita(cita_id)
                    if exito:
                        print(f"\n[✔] {mensaje}")
                    else:
                        print(f"\n[✘] Error: {mensaje}")
                else:
                    print("\n[i] Cancelación descartada.")
                    
            elif opcion == "3":
                print("\n--- REGISTRO GENERAL DE CITAS ---")
                citas = obtener_citas_filtradas(rol_actual, username_actual)
                if not citas:
                    print("No hay citas registradas en el sistema.")
                else:
                    print(f"{'ID':<4} | {'Médico':<10} | {'Estudiante':<10} | {'Fecha':<10} | {'Hora':<5} | {'Especialidad':<12} | {'Estado':<10}")
                    print("-" * 75)
                    for c in citas:
                        print(f"{c['id']:<4} | {c['medico']:<10} | {c['alumno']:<10} | {c['fecha']:<10} | {c['hora']:<5} | {c['especialidad']:<12} | {c.get('estado', 'Programada'):<10}")
                    print("\n* Nota: Por regulaciones de privacidad, los motivos médicos están cifrados en base de datos.")
                    
            elif opcion == "4":
                break
            else:
                print("\n[!] Opción no válida.")
                
        elif rol_actual == "Médico":
            print(" 1. Listar Mis Citas Médicas")
            print(" 2. Consultar Disponibilidad de Horario")
            print(" 3. Volver al Menú Principal / Salir")
            print("-" * 60)
            opcion = input("Seleccione una opción (1-3): ").strip()
            
            if opcion == "1":
                print("\n--- MIS CITAS MÉDICAS ---")
                citas = obtener_citas_filtradas(rol_actual, username_actual)
                if not citas:
                    print("No tiene citas asignadas.")
                else:
                    clave_seguridad = input("Ingrese su clave de seguridad para descifrar los diagnósticos (Presione Enter para ver sin descifrar): ").strip()
                    print("-" * 90)
                    print(f"{'ID':<4} | {'Estudiante':<10} | {'Fecha':<10} | {'Hora':<5} | {'Especialidad':<12} | {'Estado':<10} | {'Motivo Médico'}")
                    print("-" * 90)
                    for c in citas:
                        motivo_mostrar = ""
                        if c.get("cifrado"):
                            if clave_seguridad:
                                motivo_mostrar = descifrar_motivo_cita(c, clave_seguridad)
                            else:
                                motivo_mostrar = "[DATO CIFRADO - Ingrese clave]"
                        else:
                            motivo_mostrar = c.get("motivo") or "[Sin motivo]"
                        print(f"{c['id']:<4} | {c['alumno']:<10} | {c['fecha']:<10} | {c['hora']:<5} | {c['especialidad']:<12} | {c.get('estado', 'Programada'):<10} | {motivo_mostrar}")
                        
            elif opcion == "2":
                print("\n--- CONSULTAR DISPONIBILIDAD ---")
                fecha = input("Ingrese fecha a consultar (AAAA-MM-DD): ").strip()
                hora = input("Ingrese hora a consultar (HH:MM): ").strip()
                if not validar_fecha(fecha) or not validar_hora(hora):
                    print("[!] Formato de fecha u hora incorrecto.")
                    continue
                disponible = verificar_disponibilidad(username_actual, fecha, hora)
                if disponible:
                    print(f"\n[✔] Está disponible el {fecha} a las {hora}.")
                else:
                    print(f"\n[✘] Ya tiene una cita programada en ese horario.")
                    
            elif opcion == "3":
                break
            else:
                print("\n[!] Opción no válida.")
                
        elif rol_actual == "Estudiante":
            print(" 1. Solicitar/Agendar una Cita Médica")
            print(" 2. Cancelar una Cita Propia")
            print(" 3. Ver Mi Historial de Citas")
            print(" 4. Volver al Menú Principal / Salir")
            print("-" * 60)
            opcion = input("Seleccione una opción (1-4): ").strip()
            
            if opcion == "1":
                print("\n--- AGENDAR CITA ---")
                # Listar médicos para facilitar
                medicos = [u for u, d in db["usuarios"].items() if d["rol"] == "Médico"]
                if not medicos:
                    print("[!] No hay médicos registrados en el sistema actualmente.")
                    continue
                print("Médicos disponibles en el sistema:")
                for m in medicos:
                    print(f"  - {m} ({db['usuarios'][m]['nombre_completo']})")
                
                medico = input("Seleccione el nombre de usuario del Médico: ").strip().lower()
                if medico not in medicos:
                    print("[!] El usuario ingresado no es un médico válido.")
                    continue
                    
                fecha = input("Fecha deseada (AAAA-MM-DD): ").strip()
                hora = input("Hora deseada (HH:MM, ej. 09:00): ").strip()
                especialidad = input("Especialidad (ej. Odontología, Psicología): ").strip()
                motivo = input("Motivo de la consulta (será cifrado para el médico): ").strip()
                
                clave = None
                if motivo:
                    clave = input("Defina una contraseña temporal para cifrar este dato sensible: ").strip()
                    
                exito, mensaje = agendar_cita(medico, username_actual, fecha, hora, especialidad, motivo, clave)
                if exito:
                    print(f"\n[✔] {mensaje}")
                    print("[i] Guarde la clave de seguridad y compártala con su médico para que pueda leer su motivo.")
                else:
                    print(f"\n[✘] Error: {mensaje}")
                    
            elif opcion == "2":
                print("\n--- CANCELAR MI CITA ---")
                citas = obtener_citas_filtradas(rol_actual, username_actual)
                citas_activas = [c for c in citas if c.get("estado", "Programada") != "Cancelada"]
                if not citas_activas:
                    print("No tiene citas activas programadas.")
                    continue
                print("Sus citas activas:")
                for c in citas_activas:
                    print(f"  ID: {c['id']} | Médico: {c['medico']} | Fecha: {c['fecha']} | Hora: {c['hora']} | Especialidad: {c['especialidad']}")
                cita_id = input("Ingrese el ID de la cita a cancelar: ").strip()
                
                # Validar que le pertenezca al alumno
                c_valida = False
                for c in citas_activas:
                    if c["id"] == cita_id:
                        c_valida = True
                        break
                if not c_valida:
                    print("[!] Cita no válida o no le pertenece.")
                    continue
                    
                confirmacion = input(f"¿Desea cancelar la cita ID {cita_id}? (s/n): ").strip().lower()
                if confirmacion == 's':
                    exito, mensaje = cancelar_cita(cita_id)
                    if exito:
                        print(f"\n[✔] {mensaje}")
                    else:
                        print(f"\n[✘] Error: {mensaje}")
                else:
                    print("\n[i] Operación cancelada.")
                    
            elif opcion == "3":
                print("\n--- MI HISTORIAL DE CITAS ---")
                citas = obtener_citas_filtradas(rol_actual, username_actual)
                if not citas:
                    print("Usted no registra ninguna cita en el sistema.")
                else:
                    print(f"{'ID':<4} | {'Médico':<12} | {'Fecha':<10} | {'Hora':<5} | {'Especialidad':<12} | {'Estado':<10}")
                    print("-" * 60)
                    for c in citas:
                        print(f"{c['id']:<4} | {c['medico']:<12} | {c['fecha']:<10} | {c['hora']:<5} | {c['especialidad']:<12} | {c.get('estado', 'Programada'):<10}")
                        
            elif opcion == "4":
                break
            else:
                print("\n[!] Opción no válida.")
        else:
            print("[!] Su rol no tiene un panel de citas configurado.")
            break


if __name__ == "__main__":
    print("=== MEDICUS-PRIVACY: Módulo citas.py ===")
    print("Para ingresar al menú de citas de forma autónoma, inicie sesión.")
    
    user = input("Usuario: ").strip().lower()
    pw = input("Contraseña: ").strip()
    
    db = cargar_db()
    if user in db["usuarios"]:
        hash_stored = db["usuarios"][user]["password_hash"]
        
        # Validar contraseña
        acceso_concedido = False
        if seguridad:
            acceso_concedido = seguridad.verificar_password(pw, hash_stored)
        else:
            acceso_concedido = (hash_stored == f"plain${pw}" or hash_stored == pw)
            
        if acceso_concedido:
            rol = db["usuarios"][user]["rol"]
            print(f"\n[✔] Acceso concedido. Rol: {rol}")
            mostrar_menu_citas(user, rol)
        else:
            print("\n[✘] Contraseña incorrecta.")
    else:
        print("\n[✘] Usuario no registrado.")
