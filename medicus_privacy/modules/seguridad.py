"""Password hashing and authenticated encryption for sensitive medical data."""

import base64
import hashlib
import hmac
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


PASSWORD_ITERATIONS = 600_000
ENCRYPTION_ITERATIONS = 300_000
PASSWORD_PREFIX = "pbkdf2_sha256"
ENCRYPTION_PREFIX = "aesgcm"


def generar_clave():
    """Generate a 256-bit random key represented as hexadecimal text."""
    return secrets.token_hex(32)


def hash_password(password, iterations=PASSWORD_ITERATIONS):
    if not isinstance(password, str) or not password:
        raise ValueError("La contrasena no puede estar vacia.")

    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return f"{PASSWORD_PREFIX}${iterations}${salt.hex()}${password_hash.hex()}"


def verificar_password(password, password_hash):
    """Verify current hashes and the legacy salt$hash format."""
    if not isinstance(password, str) or not isinstance(password_hash, str):
        return False

    try:
        parts = password_hash.split("$")
        if len(parts) == 4 and parts[0] == PASSWORD_PREFIX:
            _, iterations_text, salt_hex, expected_hex = parts
            actual = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt_hex),
                int(iterations_text),
            )
            return hmac.compare_digest(actual, bytes.fromhex(expected_hex))

        if len(parts) == 2:
            salt_text, expected_hex = parts
            actual_hex = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt_text.encode("utf-8"),
                100_000,
            ).hex()
            return hmac.compare_digest(actual_hex, expected_hex)
    except (TypeError, ValueError):
        return False

    return False


def password_necesita_actualizacion(password_hash):
    parts = str(password_hash or "").split("$")
    return not (
        len(parts) == 4
        and parts[0] == PASSWORD_PREFIX
        and parts[1].isdigit()
        and int(parts[1]) >= PASSWORD_ITERATIONS
    )


def cifrar_datos(texto, clave):
    """Encrypt text with AES-256-GCM and a PBKDF2-derived key."""
    if texto == "":
        return ""
    if not isinstance(texto, str) or not isinstance(clave, str) or not clave:
        raise ValueError("El texto y la clave de cifrado son obligatorios.")

    salt = secrets.token_bytes(16)
    nonce = secrets.token_bytes(12)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        clave.encode("utf-8"),
        salt,
        ENCRYPTION_ITERATIONS,
        dklen=32,
    )
    encrypted = AESGCM(derived_key).encrypt(nonce, texto.encode("utf-8"), None)
    payload = base64.urlsafe_b64encode(encrypted).decode("ascii")
    return (
        f"{ENCRYPTION_PREFIX}$v1${ENCRYPTION_ITERATIONS}$"
        f"{salt.hex()}${nonce.hex()}${payload}"
    )


def descifrar_datos(texto_cifrado, clave):
    if texto_cifrado == "":
        return ""
    if not isinstance(texto_cifrado, str) or not isinstance(clave, str) or not clave:
        raise ValueError("La clave de descifrado es obligatoria.")

    if not texto_cifrado.startswith(f"{ENCRYPTION_PREFIX}$"):
        return _descifrar_legacy(texto_cifrado, clave)

    try:
        prefix, version, iterations_text, salt_hex, nonce_hex, payload = (
            texto_cifrado.split("$", 5)
        )
        if prefix != ENCRYPTION_PREFIX or version != "v1":
            raise ValueError

        derived_key = hashlib.pbkdf2_hmac(
            "sha256",
            clave.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations_text),
            dklen=32,
        )
        decrypted = AESGCM(derived_key).decrypt(
            bytes.fromhex(nonce_hex),
            base64.urlsafe_b64decode(payload.encode("ascii")),
            None,
        )
        return decrypted.decode("utf-8")
    except (InvalidTag, ValueError, UnicodeDecodeError) as exc:
        raise ValueError("Clave incorrecta o datos alterados") from exc


def _generar_keystream_legacy(clave_derivada, iv, longitud):
    keystream = bytearray()
    contador = 0
    while len(keystream) < longitud:
        bloque = clave_derivada + contador.to_bytes(4, "big") + iv
        keystream.extend(hashlib.sha256(bloque).digest())
        contador += 1
    return bytes(keystream[:longitud])


def _descifrar_legacy(texto_cifrado, clave):
    """Read records produced by the previous project version."""
    try:
        paquete = base64.b64decode(texto_cifrado.encode("utf-8"), validate=True)
        if len(paquete) < 48:
            raise ValueError

        iv = paquete[:16]
        mac_original = paquete[16:48]
        datos_cifrados = paquete[48:]
        clave_maestra = hashlib.pbkdf2_hmac(
            "sha256",
            clave.encode("utf-8"),
            iv,
            10_000,
            dklen=64,
        )
        clave_cifrado = clave_maestra[:32]
        clave_mac = clave_maestra[32:]
        mac_control = hmac.new(
            clave_mac,
            iv + datos_cifrados,
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(mac_original, mac_control):
            raise ValueError

        keystream = _generar_keystream_legacy(
            clave_cifrado,
            iv,
            len(datos_cifrados),
        )
        plano = bytes(a ^ b for a, b in zip(datos_cifrados, keystream))
        return plano.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("Clave incorrecta o datos alterados") from exc
