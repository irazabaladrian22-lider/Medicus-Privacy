"""
Script de Pruebas para seguridad.py
"""

import seguridad

def ejecutar_pruebas():
    print("=== INICIANDO PRUEBAS DE SEGURIDAD.PY ===")
    
    # 1. Prueba de generar_clave()
    print("\n[1] Probando generar_clave():")
    clave = seguridad.generar_clave()
    print(f"    Clave generada (hex): {clave}")
    print(f"    Longitud de la clave: {len(clave)} caracteres")
    assert len(clave) == 32, "Error: La clave debe tener 32 caracteres"
    print("    -> OK: Clave generada correctamente.")

    # 2. Prueba de hash_password() y verificar_password()
    print("\n[2] Probando hash y verificación de contraseñas:")
    pass_original = "MiContraseñaSegura123"
    hash_seguro = seguridad.hash_password(pass_original)
    print(f"    Contraseña: {pass_original}")
    print(f"    Hash generado: {hash_seguro}")
    
    # Verificar con contraseña correcta
    coincide = seguridad.verificar_password(pass_original, hash_seguro)
    print(f"    Verificación con contraseña correcta: {coincide}")
    assert coincide is True, "Error: La contraseña correcta debería ser validada como True"
    
    # Verificar con contraseña incorrecta
    no_coincide = seguridad.verificar_password("PasswordErroneo", hash_seguro)
    print(f"    Verificación con contraseña incorrecta: {no_coincide}")
    assert no_coincide is False, "Error: La contraseña incorrecta debería ser validada como False"
    print("    -> OK: Autenticación de contraseñas validada.")

    # 3. Prueba de cifrado y descifrado de datos (Caja Fuerte)
    print("\n[3] Probando cifrar_datos() y descifrar_datos():")
    datos_medicos = "Paciente: Juan Pérez. Diagnóstico: Hipertensión arterial. Tratamiento: Enalapril 10mg diario."
    clave_cifrado = "ClaveSecretaDelMedico"
    
    print(f"    Texto plano original: '{datos_medicos}'")
    print(f"    Clave utilizada: '{clave_cifrado}'")
    
    # Cifrar
    texto_cifrado = seguridad.cifrar_datos(datos_medicos, clave_cifrado)
    print(f"    Texto cifrado (Base64): {texto_cifrado}")
    assert texto_cifrado != datos_medicos, "Error: El texto cifrado no debe ser igual al texto plano"
    
    # Descifrar con clave correcta
    datos_descifrados = seguridad.descifrar_datos(texto_cifrado, clave_cifrado)
    print(f"    Texto descifrado: '{datos_descifrados}'")
    assert datos_descifrados == datos_medicos, "Error: Los datos descifrados no coinciden con los originales"
    
    # Intentar descifrar con clave incorrecta
    print("    Intentando descifrar con clave incorrecta...")
    error_detectado = False
    try:
        seguridad.descifrar_datos(texto_cifrado, "ClaveIncorrecta")
    except ValueError as e:
        error_detectado = True
        print(f"    Excepción capturada con éxito: {e}")
        assert str(e) == "Clave incorrecta o datos alterados", f"Error: Mensaje de excepción inesperado: '{e}'"
        
    assert error_detectado is True, "Error: El descifrado con clave incorrecta debería fallar y lanzar ValueError"
    print("    -> OK: Cifrado y descifrado validados con éxito.")

    # 4. Probar cifrado de cadena vacía
    print("\n[4] Probando casos de borde (cadenas vacías):")
    cifrado_vacio = seguridad.cifrar_datos("", clave_cifrado)
    assert cifrado_vacio == "", "Error: El cifrado de cadena vacía debe ser cadena vacía"
    descifrado_vacio = seguridad.descifrar_datos("", clave_cifrado)
    assert descifrado_vacio == "", "Error: El descifrado de cadena vacía debe ser cadena vacía"
    print("    -> OK: Casos de borde validados.")

    print("\n=== ¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE! ===")

if __name__ == "__main__":
    ejecutar_pruebas()
