"""Clinical catalogs shared by services and GUI controls."""

import unicodedata


SPECIALTIES = (
    "Medicina Interna",
    "Pediatria",
    "Ginecologia y Obstetricia",
    "Cardiologia",
    "Traumatologia y Ortopedia",
    "Odontologia",
)

SEX_OPTIONS = (
    "Femenino",
    "Masculino",
    "Otro",
    "No especificado",
)


def _key(value):
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).casefold().strip()


_SPECIALTY_MAP = {_key(value): value for value in SPECIALTIES}
_SEX_MAP = {_key(value): value for value in SEX_OPTIONS}


def normalize_specialty(value):
    return _SPECIALTY_MAP.get(_key(value))


def normalize_sex(value):
    return _SEX_MAP.get(_key(value))
