"""Authorization and encrypted longitudinal clinical histories."""

import logging
import sqlite3

from medicus_privacy.modules.clinical_crypto import (
    decrypt_clinical_text,
    encrypt_clinical_text,
)
from medicus_privacy.modules.database import DatabaseService
from medicus_privacy.modules.key_manager import ClinicalKeyManager
from medicus_privacy.modules.patients import PatientService
from medicus_privacy.modules.roles import ESTUDIANTE, MEDICO, normalizar_rol


LOGGER = logging.getLogger("Medicus-Privacy.GUI")


class ClinicalHistoryService:
    def __init__(
        self,
        actor_username,
        actor_role,
        db_path=None,
        encryption_key=None,
        key_path=None,
    ):
        self.actor_username = str(actor_username or "").strip().lower()
        self.actor_role = normalizar_rol(actor_role)
        self.database = DatabaseService(db_path)
        self.key_manager = ClinicalKeyManager(encryption_key, key_path)

    def listar_historias(self, filtro=""):
        patient_service = PatientService(
            self.actor_username,
            self.actor_role,
            self.database.db_path,
        )
        return patient_service.listar_pacientes(filtro)

    def obtener_historia(self, paciente_id):
        try:
            patient_id = int(paciente_id)
        except (TypeError, ValueError):
            return False, "Paciente no valido.", None
        with self.database.connect() as connection:
            if not self._can_read(connection, patient_id):
                return False, "No tiene acceso a esta historia clinica.", None
            patient = connection.execute(
                "SELECT * FROM pacientes WHERE id=?",
                (patient_id,),
            ).fetchone()
            if not patient:
                return False, "Paciente no encontrado.", None
            rows = connection.execute(
                """
                SELECT ev.*, u.nombre_completo AS medico,
                       c.fecha AS fecha_consulta, c.especialidad
                FROM evoluciones_clinicas ev
                JOIN historias_clinicas h ON h.id=ev.historia_id
                JOIN usuarios u ON u.id=ev.medico_id
                JOIN citas c ON c.id=ev.cita_id
                WHERE h.paciente_id=?
                ORDER BY c.fecha DESC, ev.id DESC
                """,
                (patient_id,),
            ).fetchall()

        key = self.key_manager.get_key()
        evolutions = []
        try:
            for row in rows:
                data = dict(row)
                appointment_id = data["cita_id"]
                data["diagnostico"] = decrypt_clinical_text(
                    data.pop("diagnostico_cifrado"),
                    key,
                    self._context(patient_id, appointment_id, "diagnostico"),
                )
                data["tratamiento"] = decrypt_clinical_text(
                    data.pop("tratamiento_cifrado"),
                    key,
                    self._context(patient_id, appointment_id, "tratamiento"),
                )
                evolutions.append(data)
        except ValueError as exc:
            return False, str(exc), None

        public_patient = PatientService._public(patient)
        LOGGER.info(
            "AUDITORIA | Historia consultada | Usuario: %s | Paciente ID: %s",
            self.actor_username,
            patient_id,
        )
        return True, "Historia cargada.", {
            "paciente": public_patient,
            "evoluciones": evolutions,
        }

    def agregar_evolucion(
        self,
        paciente_id,
        cita_id,
        altura_cm,
        peso_kg,
        diagnostico,
        tratamiento,
    ):
        if self.actor_role != MEDICO:
            return False, "Solo un medico puede registrar evoluciones."
        try:
            patient_id = int(paciente_id)
            appointment_id = int(cita_id)
            height = float(altura_cm)
            weight = float(peso_kg)
        except (TypeError, ValueError):
            return False, "Paciente, cita, altura y peso deben ser validos."
        if not (30 <= height <= 250):
            return False, "La altura debe estar entre 30 y 250 cm."
        if not (1 <= weight <= 500):
            return False, "El peso debe estar entre 1 y 500 kg."
        diagnosis = str(diagnostico or "").strip()
        treatment = str(tratamiento or "").strip()
        if not diagnosis or not treatment:
            return False, "Diagnostico y tratamiento son obligatorios."

        key = self.key_manager.get_key()
        encrypted_diagnosis = encrypt_clinical_text(
            diagnosis,
            key,
            self._context(patient_id, appointment_id, "diagnostico"),
        )
        encrypted_treatment = encrypt_clinical_text(
            treatment,
            key,
            self._context(patient_id, appointment_id, "tratamiento"),
        )

        with self.database.connect() as connection:
            appointment = connection.execute(
                """
                SELECT c.id, c.estado, c.paciente_id, m.id AS medico_id,
                       m.username AS medico
                FROM citas c JOIN usuarios m ON m.id=c.medico_id
                WHERE c.id=?
                """,
                (appointment_id,),
            ).fetchone()
            if not appointment or appointment["paciente_id"] != patient_id:
                return False, "La cita no pertenece al paciente."
            if appointment["medico"].casefold() != self.actor_username.casefold():
                return False, "La cita no esta asignada a este medico."
            if appointment["estado"] != "Programada":
                return False, "La cita debe estar programada y sin evolucion previa."

            connection.execute(
                """
                INSERT OR IGNORE INTO historias_clinicas (paciente_id)
                VALUES (?)
                """,
                (patient_id,),
            )
            history = connection.execute(
                "SELECT id FROM historias_clinicas WHERE paciente_id=?",
                (patient_id,),
            ).fetchone()
            try:
                connection.execute(
                    """
                    INSERT INTO evoluciones_clinicas (
                        historia_id, cita_id, medico_id, altura_cm, peso_kg,
                        diagnostico_cifrado, tratamiento_cifrado
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        history["id"],
                        appointment_id,
                        appointment["medico_id"],
                        height,
                        weight,
                        encrypted_diagnosis,
                        encrypted_treatment,
                    ),
                )
            except sqlite3.IntegrityError:
                return False, "La cita ya tiene una evolucion registrada."
            connection.execute(
                "UPDATE citas SET estado='Atendida' WHERE id=?",
                (appointment_id,),
            )
            connection.execute(
                """
                UPDATE historias_clinicas
                SET actualizado_en=CURRENT_TIMESTAMP WHERE id=?
                """,
                (history["id"],),
            )

        LOGGER.info(
            "AUDITORIA | Evolucion creada | Usuario: %s | Paciente ID: %s | Cita ID: %s",
            self.actor_username,
            patient_id,
            appointment_id,
        )
        return True, "Evolucion clinica guardada y cita marcada como atendida."

    def citas_pendientes(self, paciente_id):
        if self.actor_role != MEDICO:
            return []
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT c.id, c.fecha, c.hora, c.especialidad
                FROM citas c JOIN usuarios m ON m.id=c.medico_id
                WHERE c.paciente_id=? AND c.estado='Programada'
                  AND m.username=? COLLATE NOCASE
                ORDER BY c.fecha, c.hora
                """,
                (int(paciente_id), self.actor_username),
            ).fetchall()
        return [dict(row) for row in rows]

    def _can_read(self, connection, patient_id):
        if self.actor_role == MEDICO:
            condition = (
                "m.username=? COLLATE NOCASE "
                "AND c.estado IN ('Programada','Atendida')"
            )
            join = "JOIN usuarios m ON m.id=c.medico_id"
        elif self.actor_role == ESTUDIANTE:
            condition = "e.username=? COLLATE NOCASE AND c.estado='Atendida'"
            join = "JOIN usuarios e ON e.id=c.estudiante_id"
        else:
            return False
        return connection.execute(
            f"""
            SELECT 1 FROM citas c {join}
            WHERE c.paciente_id=? AND {condition}
            LIMIT 1
            """,
            (patient_id, self.actor_username),
        ).fetchone() is not None

    @staticmethod
    def _context(patient_id, appointment_id, field):
        return f"patient:{patient_id}|appointment:{appointment_id}|field:{field}"
