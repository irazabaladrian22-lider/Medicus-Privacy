"""
Módulo de Seguridad (Caja Fuerte) - Proyecto Medicus-Privacy
Estación de Trabajo 4: Seguridad (Cifrado)

Este módulo proporciona funciones seguras para proteger datos médicos sensibles
mediante cifrado simétrico y para gestionar el hashing seguro de contraseñas.
No tiene dependencias externas, lo que garantiza su compatibilidad en cualquier
entorno de Python 3.
"""

import base64
import hashlib
import hmac
import secrets


def generar_clave() -> str:
    """
    Genera una clave aleatoria segura de 32 caracteres hexadecimales.
    Puede ser utilizada como clave maestra para el cifrado del sistema.
    
    Retorna:
        str: Una clave aleatoria de 32 caracteres (16 bytes).
    """
    return secrets.token_hex(16)


def hash_password(password: str) -> str:
    """
    Genera un hash seguro para contraseñas utilizando PBKDF2-HMAC-SHA256
    con una sal (salt) única y aleatoria. Evita almacenar contraseñas en texto plano.
    
    Parámetros:
        password (str): La contraseña en texto plano.
        
    Retorna:
        str: Cadena con el formato 'salt$hash_hex' lista para guardar en base de datos.
    """
    # Generar sal única y aleatoria
    salt = secrets.token_hex(16)
    
    # Derivar el hash de la contraseña usando 100,000 iteraciones
    pw_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    ).hex()
    
    return f"{salt}${pw_hash}"


def verificar_password(password: str, password_hash: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con el hash almacenado.
    
    Parámetros:
        password (str): La contraseña ingresada que se desea verificar.
        password_hash (str): El hash almacenado (formato 'salt$hash_hex').
        
    Retorna:
        bool: True si la contraseña es correcta, False de lo contrario.
    """
    try:
        # Desestructurar el salt y el hash original
        salt, pw_hash = password_hash.split('$')
        
        # Calcular el hash de prueba
        pw_hash_test = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        
        # Comparación en tiempo constante para mitigar ataques de canal lateral (timing attacks)
        return hmac.compare_digest(pw_hash, pw_hash_test)
    except Exception:
        # Si el formato no coincide o hay algún error, la verificación falla
        return False


def _generar_keystream(clave_derivada: bytes, iv: bytes, longitud: int) -> bytes:
    """
    Función interna que genera una secuencia pseudoaleatoria de bytes (keystream)
    del tamaño especificado utilizando SHA-256 en modo contador.
    """
    keystream = bytearray()
    contador = 0
    while len(keystream) < longitud:
        # Concatenar la clave derivada, el contador y el IV
        bloque_datos = clave_derivada + contador.to_bytes(4, 'big') + iv
        bloque_hash = hashlib.sha256(bloque_datos).digest()
        keystream.extend(bloque_hash)
        contador += 1
    return bytes(keystream[:longitud])


def cifrar_datos(texto: str, clave: str) -> str:
    """
    Cifra un texto plano utilizando una clave y devuelve una cadena codificada en Base64.
    Implementa un cifrado de flujo con autenticación integrada (MAC).
    
    Parámetros:
        texto (str): El texto sensible que se desea proteger (ej. historia clínica).
        clave (str): La contraseña o clave secreta de cifrado.
        
    Retorna:
        str: El texto cifrado codificado en Base64 (incluye IV, MAC y datos cifrados).
    """
    if not texto:
        return ""
        
    datos_plano = texto.encode('utf-8')
    
    # Generar un Vector de Inicialización (IV) aleatorio de 16 bytes
    iv = secrets.token_bytes(16)
    
    # Derivar claves independientes para cifrado y autenticación (MAC) mediante PBKDF2
    # Esto asegura que la clave del usuario no se exponga directamente
    clave_maestra = hashlib.pbkdf2_hmac('sha256', clave.encode('utf-8'), iv, 10000, dklen=64)
    clave_cifrado = clave_maestra[:32] # 32 bytes para cifrar
    clave_mac = clave_maestra[32:]     # 32 bytes para autenticar
    
    # Generar flujo pseudoaleatorio de bytes
    keystream = _generar_keystream(clave_cifrado, iv, len(datos_plano))
    
    # Operación XOR: Cifrado simétrico
    datos_cifrados = bytes(a ^ b for a, b in zip(datos_plano, keystream))
    
    # Generar un MAC de control para autenticar la integridad de los datos
    mac = hmac.new(clave_mac, iv + datos_cifrados, hashlib.sha256).digest()
    
    # Empaquetar todo: iv (16 bytes) + mac (32 bytes) + datos_cifrados (longitud variable)
    paquete = iv + mac + datos_cifrados
    
    # Convertir a cadena Base64 imprimible
    return base64.b64encode(paquete).decode('utf-8')


def descifrar_datos(texto_cifrado_b64: str, clave: str) -> str:
    """
    Descifra un texto cifrado en Base64 usando la clave correspondiente.
    
    Parámetros:
        texto_cifrado_b64 (str): Cadena en Base64 generada por cifrar_datos().
        clave (str): La misma contraseña o clave utilizada para cifrar.
        
    Retorna:
        str: El texto original descifrado.
        
    Lanza:
        ValueError: Si la contraseña es incorrecta o los datos fueron alterados.
    """
    if not texto_cifrado_b64:
        return ""
        
    try:
        # Decodificar el paquete de Base64 a bytes
        paquete = base64.b64decode(texto_cifrado_b64.encode('utf-8'))
        
        # El paquete mínimo debe contener IV (16 bytes) + MAC (32 bytes) = 48 bytes
        if len(paquete) < 48:
            raise ValueError("Datos cifrados corruptos o incompletos")
            
        iv = paquete[:16]
        mac_original = paquete[16:48]
        datos_cifrados = paquete[48:]
        
        # Derivar de nuevo las claves usando el IV extraído
        clave_maestra = hashlib.pbkdf2_hmac('sha256', clave.encode('utf-8'), iv, 10000, dklen=64)
        clave_cifrado = clave_maestra[:32]
        clave_mac = clave_maestra[32:]
        
        # Calcular el MAC esperado
        mac_control = hmac.new(clave_mac, iv + datos_cifrados, hashlib.sha256).digest()
        
        # Validar el MAC para confirmar integridad y clave correcta
        if not hmac.compare_digest(mac_original, mac_control):
            raise ValueError("Clave incorrecta o datos alterados")
            
        # Generar la secuencia pseudoaleatoria
        keystream = _generar_keystream(clave_cifrado, iv, len(datos_cifrados))
        
        # Operación XOR: Descifrado simétrico
        datos_plano = bytes(a ^ b for a, b in zip(datos_cifrados, keystream))
        
        # Decodificar bytes a string de texto
        return datos_plano.decode('utf-8')
        
    except Exception as e:
        # Mantener el error controlado y descriptivo para el usuario
        if isinstance(e, ValueError):
            raise e
        raise ValueError("Error al descifrar los datos: formato incorrecto o clave errónea")
