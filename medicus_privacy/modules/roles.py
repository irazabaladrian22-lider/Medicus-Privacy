"""Canonical roles shared by authentication, administration and appointments."""

import unicodedata


ADMIN = "Admin"
MEDICO = "Medico"
RECEPCIONISTA = "Recepcionista"
ESTUDIANTE = "Estudiante"

ROLES_PERMITIDOS = (ADMIN, MEDICO, RECEPCIONISTA, ESTUDIANTE)


def _normalizar_texto(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    return "".join(
        char for char in texto if not unicodedata.combining(char)
    ).casefold().strip()


_ALIASES = {
    "admin": ADMIN,
    "administrador": ADMIN,
    "medico": MEDICO,
    "recep": RECEPCIONISTA,
    "recepcion": RECEPCIONISTA,
    "recepcionista": RECEPCIONISTA,
    "estudiante": ESTUDIANTE,
    "alumno": ESTUDIANTE,
    "paciente": ESTUDIANTE,
}


def normalizar_rol(rol):
    """Return the canonical role or None when the value is unknown."""
    return _ALIASES.get(_normalizar_texto(rol))


def rol_valido(rol):
    return normalizar_rol(rol) in ROLES_PERMITIDOS
