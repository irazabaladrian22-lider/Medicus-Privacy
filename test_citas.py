"""
Script de pruebas automatizadas para citas.py
"""

import os
import json
import admin
import citas
import seguridad

# Rutas para el respaldo de la base de datos durante las pruebas
DB_PATH = citas.DB_PATH
DB_BACKUP_PATH = DB_PATH + ".backup"


def respaldar_db():
    """Respalda la base de datos actual para no perder datos reales."""
    if os.path.exists(DB_PATH):
        os.rename(DB_PATH, DB_BACKUP_PATH)


def restaurar_db():
    """Restaura la base de datos original."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    if os.path.exists(DB_BACKUP_PATH):
        os.rename(DB_BACKUP_PATH, DB_PATH)


def ejecutar_pruebas():
    print("=== INICIANDO PRUEBAS DE CITAS.PY ===")
    
    respaldar_db()
    
    try:
        # 1. Configurar un ambiente limpio con usuarios de prueba
        admin.cargar_db()
        
        # Registrar un médico y un estudiante para poder agendar citas
        exito_m, _ = admin.crear_usuario("medico_citas", "pass123", "Médico", "Dr. Cardiólogo Test")
        exito_e, _ = admin.crear_usuario("alumno_citas", "pass123", "Estudiante", "Estudiante Juan Test")
        
        assert exito_m is True and exito_e is True, "Error: No se pudieron configurar los usuarios de prueba."
        print("[1] Usuarios de prueba configurados correctamente.")
        
        # 2. Probar agendar una cita normal (sin cifrado)
        print("\n[2] Probando agendar_cita() normal:")
        exito, msg = citas.agendar_cita(
            medico_username="medico_citas",
            alumno_username="alumno_citas",
            fecha="2026-07-10",
            hora="09:00",
            especialidad="Cardiología",
            motivo_sensible=""
        )
        print(f"    Cita normal: {exito} - {msg}")
        assert exito is True, f"Error al agendar cita: {msg}"
        
        # 3. Probar colisiones de horario (Disponibilidad)
        print("\n[3] Probando verificar_disponibilidad() y colisiones:")
        
        # Verificar que el médico ya no esté disponible
        disponible = citas.verificar_disponibilidad("medico_citas", "2026-07-10", "09:00")
        print(f"    Disponibilidad del médico el 2026-07-10 a las 09:00: {disponible} (Esperado: False)")
        assert disponible is False, "Error: El médico debería reportarse como ocupado."
        
        # Intentar agendar otra cita en el mismo horario con el mismo médico (debería fallar)
        exito_colision, msg_colision = citas.agendar_cita(
            medico_username="medico_citas",
            alumno_username="alumno_citas",
            fecha="2026-07-10",
            hora="09:00",
            especialidad="Cardiología",
            motivo_sensible=""
        )
        print(f"    Agendar cita colisionada: {exito_colision} - {msg_colision}")
        assert exito_colision is False, "Error: Se permitió agendar una cita duplicada en el mismo horario."
        
        # 4. Probar agendamiento de cita segura (Con Cifrado)
        print("\n[4] Probando agendar_cita() segura (Cifrada):")
        motivo_secreto = "El paciente reporta taquicardia severa por las noches."
        clave_secreta = "ClaveSecreta123"
        
        exito_segura, msg_segura = citas.agendar_cita(
            medico_username="medico_citas",
            alumno_username="alumno_citas",
            fecha="2026-07-10",
            hora="10:00",
            especialidad="Cardiología",
            motivo_sensible=motivo_secreto,
            clave_seguridad=clave_secreta
        )
        print(f"    Cita segura: {exito_segura} - {msg_segura}")
        assert exito_segura is True, f"Error al agendar cita segura: {msg_segura}"
        
        # Verificar persistencia cifrada en BD
        db_actual = citas.cargar_db()
        cita_segura = next(c for c in db_actual["citas"] if c["hora"] == "10:00")
        print(f"    Registro guardado en JSON: {cita_segura}")
        assert cita_segura["cifrado"] is True, "Error: La cita debería figurar como cifrada en base de datos."
        assert cita_segura["motivo"] != motivo_secreto, "Error: El motivo médico confidencial se guardó en texto plano."
        
        # 5. Probar descifrado con clave correcta e incorrecta
        print("\n[5] Probando descifrado de motivos médicos:")
        
        # Descifrar con clave correcta
        texto_descifrado = citas.descifrar_motivo_cita(cita_segura, clave_secreta)
        print(f"    Descifrado con clave correcta: '{texto_descifrado}'")
        assert texto_descifrado == motivo_secreto, "Error: El motivo descifrado no coincide con el original."
        
        # Descifrar con clave incorrecta
        texto_error_clave = citas.descifrar_motivo_cita(cita_segura, "ClaveErrada")
        print(f"    Descifrado con clave incorrecta: '{texto_error_clave}'")
        assert "Clave Incorrecta" in texto_error_clave, "Error: Debería reportar error por clave incorrecta."
        
        # Descifrar sin clave
        texto_sin_clave = citas.descifrar_motivo_cita(cita_segura, None)
        print(f"    Descifrado sin clave: '{texto_sin_clave}'")
        assert "Requiere Clave" in texto_sin_clave, "Error: Debería avisar que requiere clave."
        
        # 6. Probar cancelación de citas
        print("\n[6] Probando cancelar_cita():")
        
        # Obtener id de la primera cita
        id_cita_normal = db_actual["citas"][0]["id"]
        exito_cancel, msg_cancel = citas.cancelar_cita(id_cita_normal)
        print(f"    Cancelar cita normal: {exito_cancel} - {msg_cancel}")
        assert exito_cancel is True, f"Error al cancelar cita: {msg_cancel}"
        
        # Verificar estado en BD
        db_despues = citas.cargar_db()
        assert db_despues["citas"][0]["estado"] == "Cancelada", "Error: El estado de la cita no cambió a 'Cancelada'."
        
        # Verificar que el médico ahora esté libre en ese horario tras la cancelación
        disponible_post_cancel = citas.verificar_disponibilidad("medico_citas", "2026-07-10", "09:00")
        print(f"    Disponibilidad tras cancelar: {disponible_post_cancel} (Esperado: True)")
        assert disponible_post_cancel is True, "Error: El médico debería estar libre tras la cancelación de la cita."
        
        print("\n=== ¡TODAS LAS PRUEBAS DE CITAS.PY PASARON EXITOSAMENTE! ===")
        
    finally:
        restaurar_db()


if __name__ == "__main__":
    ejecutar_pruebas()
