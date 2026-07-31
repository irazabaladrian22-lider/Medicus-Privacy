"""Patient registry without patient login accounts."""

import re
import sqlite3
from datetime import date

from medicus_privacy.modules.catalogs import normalize_sex
from medicus_privacy.modules.database import DatabaseService
from medicus_privacy.modules.roles import (
    ADMIN,
    ESTUDIANTE,
    MEDICO,
    RECEPCIONISTA,
    normalizar_rol,
)


CEDULA_PATTERN = re.compile(r"^[A-Z0-9-]{5,20}$")
WRITE_ROLES = (ADMIN, RECEPCIONISTA, MEDICO)


def normalize_cedula(value):
    return re.sub(r"\s+", "", str(value or "")).upper()


def calculate_age(birth_date, today=None):
    born = date.fromisoformat(str(birth_date))
    current = today or date.today()
    return current.year - born.year - (
        (current.month, current.day) < (born.month, born.day)
    )


class PatientService:
    def __init__(self, actor_username, actor_role, db_path=None):
        self.actor_username = str(actor_username or "").strip().lower()
        self.actor_role = normalizar_rol(actor_role)
        self.database = DatabaseService(db_path)

    @staticmethod
    def validate_profile(
        cedula,
        nombres,
        apellidos,
        fecha_nacimiento,
        sexo,
    ):
        normalized_id = normalize_cedula(cedula)
        if not CEDULA_PATTERN.fullmatch(normalized_id):
            return None, "La cedula debe tener entre 5 y 20 letras, numeros o guiones."
        names = str(nombres or "").strip()
        surnames = str(apellidos or "").strip()
        if not names or not surnames:
            return None, "Nombres y apellidos son obligatorios."
        try:
            born = date.fromisoformat(str(fecha_nacimiento))
        except (TypeError, ValueError):
            return None, "Seleccione una fecha de nacimiento valida."
        if born >= date.today():
            return None, "La fecha de nacimiento debe ser anterior a hoy."
        normalized_sex = normalize_sex(sexo)
        if not normalized_sex:
            return None, "Seleccione un sexo valido."
        return (normalized_id, names, surnames, born.isoformat(), normalized_sex), None

    def registrar_paciente(
        self,
        cedula,
        nombres,
        apellidos,
        fecha_nacimiento,
        sexo,
        nacionalidad="",
        direccion="",
    ):
        if self.actor_role not in WRITE_ROLES:
            return False, "Su rol no puede registrar pacientes.", None
        values, error = self.validate_profile(
            cedula,
            nombres,
            apellidos,
            fecha_nacimiento,
            sexo,
        )
        if error:
            return False, error, None
        try:
            with self.database.connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO pacientes (
                        cedula, nombres, apellidos, fecha_nacimiento, sexo,
                        nacionalidad, direccion, datos_completos
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        *values,
                        str(nacionalidad or "").strip(),
                        str(direccion or "").strip(),
                    ),
                )
            return True, "Paciente registrado correctamente.", cursor.lastrowid
        except sqlite3.IntegrityError:
            return False, "Ya existe un paciente con esa cedula.", None

    def actualizar_paciente(
        self,
        patient_id,
        cedula,
        nombres,
        apellidos,
        fecha_nacimiento,
        sexo,
        nacionalidad="",
        direccion="",
    ):
        if self.actor_role not in WRITE_ROLES:
            return False, "Su rol no puede editar pacientes."
        values, error = self.validate_profile(
            cedula,
            nombres,
            apellidos,
            fecha_nacimiento,
            sexo,
        )
        if error:
            return False, error
        try:
            with self.database.connect() as connection:
                result = connection.execute(
                    """
                    UPDATE pacientes
                    SET cedula=?, nombres=?, apellidos=?, fecha_nacimiento=?,
                        sexo=?, nacionalidad=?, direccion=?, datos_completos=1,
                        actualizado_en=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (
                        *values,
                        str(nacionalidad or "").strip(),
                        str(direccion or "").strip(),
                        int(patient_id),
                    ),
                )
                if result.rowcount == 0:
                    return False, "Paciente no encontrado."
            return True, "Paciente actualizado correctamente."
        except (ValueError, sqlite3.IntegrityError):
            return False, "La cedula ya pertenece a otro paciente."

    def buscar_por_cedula(self, cedula):
        normalized = normalize_cedula(cedula)
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM pacientes WHERE cedula = ? COLLATE NOCASE",
                (normalized,),
            ).fetchone()
        return self._public(row) if row else None

    def listar_pacientes(self, filtro=""):
        if self.actor_role in (ADMIN, RECEPCIONISTA):
            access_sql, params = "", []
        elif self.actor_role == MEDICO:
            access_sql = """
                WHERE EXISTS (
                    SELECT 1 FROM citas c
                    JOIN usuarios m ON m.id=c.medico_id
                    WHERE c.paciente_id=p.id AND m.username=? COLLATE NOCASE
                      AND c.estado IN ('Programada','Atendida')
                )
            """
            params = [self.actor_username]
        elif self.actor_role == ESTUDIANTE:
            access_sql = """
                WHERE EXISTS (
                    SELECT 1 FROM citas c
                    JOIN usuarios e ON e.id=c.estudiante_id
                    WHERE c.paciente_id=p.id AND e.username=? COLLATE NOCASE
                      AND c.estado='Atendida'
                )
            """
            params = [self.actor_username]
        else:
            return []

        filter_value = f"%{str(filtro or '').strip()}%"
        connector = " AND " if access_sql else " WHERE "
        if filtro:
            access_sql += (
                connector
                + "(p.cedula LIKE ? OR p.nombres LIKE ? OR p.apellidos LIKE ?)"
            )
            params.extend([filter_value, filter_value, filter_value])
        with self.database.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT p.* FROM pacientes p
                {access_sql}
                ORDER BY p.apellidos, p.nombres
                """,
                params,
            ).fetchall()
        return [self._public(row) for row in rows]

    @staticmethod
    def _public(row):
        data = dict(row)
        data["edad"] = (
            calculate_age(data["fecha_nacimiento"])
            if data.get("fecha_nacimiento")
            else None
        )
        data["nombre_completo"] = (
            f"{data['nombres']} {data['apellidos']}".strip()
        )
        return data
