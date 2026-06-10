"""
Authentication service for Medicus-Privacy.

The public method used by Main.py is:
    verificar_credenciales(usuario, password) -> (success, role, user_data)
"""

import hashlib
import hmac
import json
from pathlib import Path


ALLOWED_ROLES = {"Admin", "Medico", "Recepcionista", "Estudiante"}
PBKDF2_ITERATIONS = 120_000


class AuthConfigurationError(Exception):
    """Raised when the local users file is missing or malformed."""


class AuthService:
    def __init__(self, users_file=None):
        project_root = Path(__file__).resolve().parents[2]
        self.users_file = Path(users_file) if users_file else project_root / "data" / "users.json"
        self.users = self._load_users()

    def verificar_credenciales(self, usuario, password):
        """
        Validate user credentials.

        Returns:
            (True, role, user_data) on success.
            (False, None, None) on invalid credentials or invalid role.
        """
        username = (usuario or "").strip()
        if not username or password is None:
            return False, None, None

        user = self._find_user(username)
        if not user or not user.get("activo", True):
            return False, None, None

        role = user.get("rol")
        if role not in ALLOWED_ROLES:
            return False, None, None

        if not self._verify_password(password, user):
            return False, None, None

        user_data = {
            "user_id": user["user_id"],
            "nombre": user["nombre"],
            "usuario": user["usuario"],
            "rol": role,
        }
        return True, role, user_data

    def _load_users(self):
        if not self.users_file.exists():
            raise AuthConfigurationError(f"Users file not found: {self.users_file}")

        try:
            data = json.loads(self.users_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise AuthConfigurationError(f"Invalid users JSON: {exc}") from exc

        users = data.get("usuarios")
        if not isinstance(users, list):
            raise AuthConfigurationError("users.json must contain a 'usuarios' list")

        return users

    def _find_user(self, username):
        normalized = username.casefold()
        for user in self.users:
            if str(user.get("usuario", "")).casefold() == normalized:
                return user
        return None

    def _verify_password(self, password, user):
        salt_hex = user.get("salt")
        expected_hash = user.get("password_hash")
        if not salt_hex or not expected_hash:
            return False

        try:
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(expected_hash)
        except ValueError:
            return False

        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            PBKDF2_ITERATIONS,
        )
        return hmac.compare_digest(actual, expected)


def generar_hash_password(password):
    """
    Helper for future user creation.

    Returns a dict with salt and password_hash. Not used by login directly.
    """
    import secrets

    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return {
        "salt": salt.hex(),
        "password_hash": password_hash.hex(),
    }
