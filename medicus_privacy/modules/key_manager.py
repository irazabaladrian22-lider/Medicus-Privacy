"""Application-managed clinical key protected by Windows DPAPI."""

import base64
import ctypes
import os
import secrets
from ctypes import wintypes
from pathlib import Path


ENV_KEY = "MEDICUS_MASTER_KEY"
KEY_BYTES = 32
CRYPTPROTECT_UI_FORBIDDEN = 0x1


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _decode_env_key(value):
    try:
        raw = base64.urlsafe_b64decode(str(value).encode("ascii"))
    except Exception as exc:
        raise RuntimeError(f"{ENV_KEY} no contiene Base64 valido.") from exc
    if len(raw) != KEY_BYTES:
        raise RuntimeError(f"{ENV_KEY} debe representar exactamente 32 bytes.")
    return raw


def _blob_from_bytes(data):
    buffer = ctypes.create_string_buffer(data)
    blob = _DataBlob(
        len(data),
        ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)),
    )
    return blob, buffer


def _dpapi_protect(data):
    if os.name != "nt":
        raise RuntimeError(
            f"Defina {ENV_KEY} fuera de Windows para proteger datos clinicos."
        )
    source, source_buffer = _blob_from_bytes(data)
    destination = _DataBlob()
    result = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(source),
        "MedicusPrivacy clinical key",
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(destination),
    )
    del source_buffer
    if not result:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(destination.pbData, destination.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(destination.pbData)


def _dpapi_unprotect(data):
    if os.name != "nt":
        raise RuntimeError(
            f"Defina {ENV_KEY} fuera de Windows para leer datos clinicos."
        )
    source, source_buffer = _blob_from_bytes(data)
    destination = _DataBlob()
    result = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(source),
        None,
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(destination),
    )
    del source_buffer
    if not result:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(destination.pbData, destination.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(destination.pbData)


class ClinicalKeyManager:
    def __init__(self, explicit_key=None, key_path=None):
        self.explicit_key = explicit_key
        default_root = Path(
            os.environ.get("LOCALAPPDATA", Path.home() / ".medicus_privacy")
        )
        self.key_path = Path(
            key_path or default_root / "MedicusPrivacy" / "clinical.key"
        )

    def get_key(self):
        if self.explicit_key is not None:
            key = self.explicit_key
            if isinstance(key, str):
                key = _decode_env_key(key)
            if not isinstance(key, bytes) or len(key) != KEY_BYTES:
                raise ValueError("La clave clinica debe tener 32 bytes.")
            return key

        configured = os.environ.get(ENV_KEY)
        if configured:
            return _decode_env_key(configured)

        if self.key_path.exists():
            return _dpapi_unprotect(self.key_path.read_bytes())

        key = secrets.token_bytes(KEY_BYTES)
        protected = _dpapi_protect(key)
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        self.key_path.write_bytes(protected)
        return key
