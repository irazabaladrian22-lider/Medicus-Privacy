"""Appointment service for staff, patients and clinical trainees."""

import sqlite3
from datetime import datetime

from medicus_privacy.modules.catalogs import normalize_specialty
from medicus_privacy.modules.database import DatabaseService
from medicus_privacy.modules.roles import (
    ADMIN,
    ESTUDIANTE,
    MEDICO,
    RECEPCIONISTA,
    normalizar_rol,
)


START_HOUR = 7
END_HOUR = 19
SLOT_MINUTES = (0, 30)
SCHEDULING_ROLES = (ADMIN, RECEPCIONISTA, MEDICO)


class CitasService:
    def __init__(self, actor_username, actor_role, db_path=None):
        self.actor_username = str(actor_username or "").strip().lower()
        self.actor_role = normalizar_rol(actor_role)
        self.database = DatabaseService(db_path)

    @staticmethod
    def validar_fecha_hora(fecha, hora, now=None):
        try:
            value = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
        except (TypeError, ValueError):
            return False, "Seleccione una fecha y hora validas."
        if value <= (now or datetime.now()):
            return False, "La cita debe programarse en una fecha y hora futuras."
        if (
            value.hour < START_HOUR
            or value.hour > END_HOUR
            or value.minute not in SLOT_MINUTES
            or (value.hour == END_HOUR and value.minute != 0)
        ):
            return (
                False,
                "Seleccione un horario entre 07:00 y 19:00 en bloques de 30 minutos.",
            )
        return True, ""

    @staticmethod
    def validar_fecha(fecha):
        return CitasService.validar_fecha_hora(fecha, "12:00")[0]

    @staticmethod
    def validar_hora(hora):
        try:
            value = datetime.strptime(str(hora), "%H:%M")
        except (TypeError, ValueError):
            return False
        return (
            START_HOUR <= value.hour <= END_HOUR
            and value.minute in SLOT_MINUTES
            and not (value.hour == END_HOUR and value.minute != 0)
        )

    def verificar_disponibilidad(self, medico_username, fecha, hora):
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) FROM citas c
                JOIN usuarios m ON m.id=c.medico_id
                WHERE m.username=? COLLATE NOCASE AND c.fecha=? AND c.hora=?
                  AND c.estado='Programada'
                """,
                (str(medico_username).strip().lower(), fecha, hora),
            ).fetchone()
        return row[0] == 0

    def agendar_cita(
        self,
        medico_username,
        paciente_id,
        fecha,
        hora,
        especialidad,
        estudiante_username=None,
    ):
        if self.actor_role not in SCHEDULING_ROLES:
            return False, "Su rol no tiene permiso para agendar citas."
        doctor_username = str(medico_username or "").strip().lower()
        student_username = str(estudiante_username or "").strip().lower() or None
        specialty = normalize_specialty(especialidad)
        if self.actor_role == MEDICO and doctor_username != self.actor_username:
            return False, "Un medico solo puede agendar sus propias consultas."
        if not specialty:
            return False, "Seleccione una especialidad valida."
        valid, message = self.validar_fecha_hora(str(fecha), str(hora))
        if not valid:
            return False, message
        try:
            patient_id = int(paciente_id)
        except (TypeError, ValueError):
            return False, "Seleccione un paciente valido."

        try:
            with self.database.connect() as connection:
                doctor = self._active_staff(
                    connection,
                    doctor_username,
                    MEDICO,
                    specialty,
                )
                if not doctor:
                    return (
                        False,
                        "El medico no esta activo o no pertenece a la especialidad.",
                    )
                patient = connection.execute(
                    "SELECT id, datos_completos FROM pacientes WHERE id=?",
                    (patient_id,),
                ).fetchone()
                if not patient:
                    return False, "El paciente no existe."
                if not patient["datos_completos"]:
                    return False, "Complete los datos del paciente antes de agendar."

                student_id = None
                if student_username:
                    if self.actor_role not in (ADMIN, RECEPCIONISTA):
                        return False, "Solo Admin o Recepcion pueden asignar estudiantes."
                    student = self._active_staff(
                        connection,
                        student_username,
                        ESTUDIANTE,
                        specialty,
                    )
                    if not student:
                        return (
                            False,
                            "El estudiante no esta activo o no pertenece a la especialidad.",
                        )
                    student_id = student["id"]

                cursor = connection.execute(
                    """
                    INSERT INTO citas (
                        medico_id, paciente_id, estudiante_id, fecha, hora,
                        especialidad, estado
                    ) VALUES (?, ?, ?, ?, ?, ?, 'Programada')
                    """,
                    (
                        doctor["id"],
                        patient_id,
                        student_id,
                        str(fecha),
                        str(hora),
                        specialty,
                    ),
                )
            return True, f"Cita ID {cursor.lastrowid} agendada correctamente."
        except sqlite3.IntegrityError:
            return (
                False,
                "El medico, paciente o estudiante ya tiene una cita en ese horario.",
            )

    def cancelar_cita(self, cita_id):
        try:
            appointment_id = int(cita_id)
        except (TypeError, ValueError):
            return False, "El ID de la cita no es valido."
        with self.database.connect() as connection:
            appointment = connection.execute(
                """
                SELECT c.id, c.estado, m.username AS medico
                FROM citas c JOIN usuarios m ON m.id=c.medico_id
                WHERE c.id=?
                """,
                (appointment_id,),
            ).fetchone()
            if not appointment:
                return False, "La cita no existe."
            if appointment["estado"] != "Programada":
                return False, "Solo se pueden cancelar citas programadas."
            allowed = self.actor_role in (ADMIN, RECEPCIONISTA) or (
                self.actor_role == MEDICO
                and appointment["medico"].casefold()
                == self.actor_username.casefold()
            )
            if not allowed:
                return False, "No tiene permiso para cancelar esta cita."
            connection.execute(
                "UPDATE citas SET estado='Cancelada' WHERE id=?",
                (appointment_id,),
            )
        return True, f"Cita ID {appointment_id} cancelada correctamente."

    def obtener_citas(self):
        clauses = []
        params = []
        if self.actor_role == MEDICO:
            clauses.append("m.username=? COLLATE NOCASE")
            params.append(self.actor_username)
        elif self.actor_role == ESTUDIANTE:
            clauses.append("e.username=? COLLATE NOCASE")
            params.append(self.actor_username)
        elif self.actor_role not in (ADMIN, RECEPCIONISTA):
            return []
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.database.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT c.id, c.paciente_id, p.cedula,
                       p.nombres || ' ' || p.apellidos AS paciente,
                       m.username AS medico,
                       COALESCE(e.username, '') AS estudiante,
                       c.fecha, c.hora, c.especialidad, c.estado
                FROM citas c
                JOIN pacientes p ON p.id=c.paciente_id
                JOIN usuarios m ON m.id=c.medico_id
                LEFT JOIN usuarios e ON e.id=c.estudiante_id
                {where}
                ORDER BY c.fecha DESC, c.hora DESC, c.id DESC
                """,
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _active_staff(connection, username, role, specialty):
        return connection.execute(
            """
            SELECT id, username FROM usuarios
            WHERE username=? COLLATE NOCASE AND rol=? AND especialidad=?
              AND activo=1
            """,
            (username, role, specialty),
        ).fetchone()


def mostrar_menu_citas(datos_usuario, db_path=None):
    service = CitasService(
        datos_usuario.get("usuario"),
        datos_usuario.get("rol"),
        db_path,
    )
    print("Citas disponibles:")
    for appointment in service.obtener_citas():
        print(
            f"{appointment['id']} | {appointment['fecha']} "
            f"{appointment['hora']} | {appointment['paciente']} | "
            f"{appointment['estado']}"
        )
