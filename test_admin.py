"""
Script de pruebas automatizadas para admin.py
"""

import os
import json
import admin
import seguridad

# Rutas para el respaldo de la base de datos durante las pruebas
DB_PATH = admin.DB_PATH
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
    print("=== INICIANDO PRUEBAS DE ADMIN.PY ===")
    
    respaldar_db()
    
    try:
        # 1. Asegurar base de datos inicializada
        db = admin.cargar_db()
        print("[1] Base de datos cargada/inicializada correctamente.")
        assert "admin" in db["usuarios"], "Error: El usuario admin por defecto debería estar presente."
        assert db["usuarios"]["admin"]["rol"] == "Admin", "Error: Rol de admin incorrecto."
        
        # 2. Probar creación de nuevos usuarios
        print("\n[2] Probando crear_usuario():")
        
        # Médico
        exito, msg = admin.crear_usuario("medico_test", "medico123", "Médico", "Dr. Carlos Test")
        print(f"    Crear Médico: {exito} - {msg}")
        assert exito is True, f"Error al crear médico: {msg}"
        
        # Estudiante
        exito, msg = admin.crear_usuario("estudiante_test", "alumno123", "Estudiante", "Juan Alumno Test")
        print(f"    Crear Estudiante: {exito} - {msg}")
        assert exito is True, f"Error al crear estudiante: {msg}"
        
        # Recepción
        exito, msg = admin.crear_usuario("recep_test", "recep123", "Recep", "María Recepción Test")
        print(f"    Crear Recep: {exito} - {msg}")
        assert exito is True, f"Error al crear recep: {msg}"
        
        # 3. Validar duplicados y restricciones
        print("\n[3] Probando validaciones y casos incorrectos:")
        
        # Duplicado
        exito, msg = admin.crear_usuario("medico_test", "otra123", "Médico", "Duplicado")
        print(f"    Intentar duplicado: {exito} - {msg}")
        assert exito is False, "Error: Se permitió crear un usuario duplicado."
        
        # Rol inválido
        exito, msg = admin.crear_usuario("otro_test", "pass123", "SuperAdmin", "Usuario Inválido")
        print(f"    Intentar rol no autorizado: {exito} - {msg}")
        assert exito is False, "Error: Se permitió crear un usuario con un rol no registrado."
        
        # Contraseña corta
        exito, msg = admin.crear_usuario("corto", "12", "Médico", "Corto")
        print(f"    Intentar pass corto: {exito} - {msg}")
        assert exito is False, "Error: Se permitió crear un usuario con contraseña corta."

        # 4. Probar listar usuarios
        print("\n[4] Probando listar_usuarios():")
        usuarios = admin.listar_usuarios()
        print(f"    Lista obtenida: {usuarios}")
        nombres_usuario = [u["username"] for u in usuarios]
        assert "medico_test" in nombres_usuario, "Error: medico_test no se encuentra en la lista."
        assert "estudiante_test" in nombres_usuario, "Error: estudiante_test no se encuentra en la lista."
        print("    -> OK: Listado de usuarios validado.")

        # 5. Probar actualización de roles
        print("\n[5] Probando actualizar_rol_usuario():")
        exito, msg = admin.actualizar_rol_usuario("recep_test", "Admin")
        print(f"    Cambiar rol: {exito} - {msg}")
        assert exito is True, f"Error al actualizar rol: {msg}"
        
        db_actual = admin.cargar_db()
        assert db_actual["usuarios"]["recep_test"]["rol"] == "Admin", "Error: Rol no se actualizó en la BD."
        print("    -> OK: Cambio de rol validado.")

        # 6. Probar eliminación de usuarios (Baja)
        print("\n[6] Probando eliminar_usuario():")
        
        # Eliminar recep_test (ahora Admin temporal)
        exito, msg = admin.eliminar_usuario("recep_test")
        print(f"    Eliminar usuario existente: {exito} - {msg}")
        assert exito is True, f"Error al eliminar usuario: {msg}"
        
        # Intentar eliminar único administrador (admin)
        exito, msg = admin.eliminar_usuario("admin")
        print(f"    Intentar eliminar único Admin principal: {exito} - {msg}")
        assert exito is False, "Error: Se permitió eliminar al único Administrador."
        
        # Intentar eliminar inexistente
        exito, msg = admin.eliminar_usuario("invalido_test")
        print(f"    Intentar eliminar inexistente: {exito} - {msg}")
        assert exito is False, "Error: Se reportó éxito al eliminar usuario inexistente."
        
        print("\n=== ¡TODAS LAS PRUEBAS DE ADMIN.PY PASARON EXITOSAMENTE! ===")
        
    finally:
        restaurar_db()


if __name__ == "__main__":
    ejecutar_pruebas()
