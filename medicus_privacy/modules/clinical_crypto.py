"""AES-GCM helpers for application-managed clinical encryption."""

import base64
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


PREFIX = "clinical$v1$"


def encrypt_clinical_text(text, key, context):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("El contenido clinico no puede estar vacio.")
    if not isinstance(key, bytes) or len(key) != 32:
        raise ValueError("La clave clinica debe tener 32 bytes.")
    nonce = secrets.token_bytes(12)
    encrypted = AESGCM(key).encrypt(
        nonce,
        text.strip().encode("utf-8"),
        str(context).encode("utf-8"),
    )
    payload = base64.urlsafe_b64encode(nonce + encrypted).decode("ascii")
    return PREFIX + payload


def decrypt_clinical_text(token, key, context):
    if not isinstance(token, str) or not token.startswith(PREFIX):
        raise ValueError("Formato clinico cifrado no reconocido.")
    try:
        raw = base64.urlsafe_b64decode(token[len(PREFIX) :].encode("ascii"))
        plain = AESGCM(key).decrypt(
            raw[:12],
            raw[12:],
            str(context).encode("utf-8"),
        )
        return plain.decode("utf-8")
    except (InvalidTag, ValueError, UnicodeDecodeError) as exc:
        raise ValueError("Contenido clinico alterado o clave no disponible.") from exc
