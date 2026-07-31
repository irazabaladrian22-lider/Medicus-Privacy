import sqlite3
import unittest
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

from medicus_privacy.modules.admin import AdminService
from medicus_privacy.modules.citas import CitasService
from medicus_privacy.modules.clinical import ClinicalHistoryService
from medicus_privacy.modules.patients import PatientService, calculate_age
from medicus_privacy.modules.roles import (
    ADMIN,
    ESTUDIANTE,
    MEDICO,
    RECEPCIONISTA,
)


class ClinicalTests(unittest.TestCase):
    KEY = b"k" * 32

    @classmethod
    def setUpClass(cls):
        cls.db_path = Path(__file__).resolve().parent / ".test_clinical.db"

    @classmethod
    def tearDownClass(cls):
        cls.db_path.unlink(missing_ok=True)

    def setUp(self):
        self.db_path.unlink(missing_ok=True)
        admin = AdminService(ADMIN, self.db_path)
        for username, role, specialty in (
            ("doctor_one", MEDICO, "Cardiologia"),
            ("doctor_two", MEDICO, "Cardiologia"),
            ("student_one", ESTUDIANTE, "Cardiologia"),
        ):
            admin.crear_usuario(
                username,
                "Password123",
                role,
                username.replace("_", " ").title(),
                specialty,
            )
        patients = PatientService("admin", ADMIN, self.db_path)
        success, message, self.patient_id = patients.registrar_paciente(
            "V-11223344",
            "Maria",
            "Lopez",
            "2000-07-15",
            "Femenino",
            "Venezolana",
            "Caracas",
        )
        self.assertTrue(success, message)
        self.future = (date.today() + timedelta(days=5)).isoformat()
        reception = CitasService("recepcion", RECEPCIONISTA, self.db_path)
        self.assertTrue(
            reception.agendar_cita(
                "doctor_one",
                self.patient_id,
                self.future,
                "09:00",
                "Cardiologia",
                "student_one",
            )[0]
        )
        self.appointment_id = reception.obtener_citas()[0]["id"]

    def history(self, username, role):
        return ClinicalHistoryService(
            username,
            role,
            self.db_path,
            self.KEY,
        )

    def test_patient_identity_age_and_duplicate(self):
        patients = PatientService("admin", ADMIN, self.db_path)
        patient = patients.buscar_por_cedula("v-11223344")
        self.assertEqual(patient["nombre_completo"], "Maria Lopez")
        self.assertEqual(
            patient["edad"],
            calculate_age("2000-07-15"),
        )
        self.assertFalse(
            patients.registrar_paciente(
                "V-11223344",
                "Otra",
                "Persona",
                "1990-01-01",
                "Femenino",
            )[0]
        )

    def test_encrypted_evolution_permissions_and_continuity(self):
        doctor = self.history("doctor_one", MEDICO)
        success, message = doctor.agregar_evolucion(
            self.patient_id,
            self.appointment_id,
            165,
            62,
            "Diagnostico reservado",
            "Tratamiento reservado",
        )
        self.assertTrue(success, message)

        with closing(sqlite3.connect(self.db_path)) as connection:
            encrypted = connection.execute(
                """
                SELECT diagnostico_cifrado, tratamiento_cifrado
                FROM evoluciones_clinicas
                """
            ).fetchone()
        self.assertNotIn("Diagnostico reservado", encrypted[0])
        self.assertNotIn("Tratamiento reservado", encrypted[1])

        success, _, history = doctor.obtener_historia(self.patient_id)
        self.assertTrue(success)
        self.assertEqual(
            history["evoluciones"][0]["diagnostico"],
            "Diagnostico reservado",
        )
        self.assertTrue(
            self.history("student_one", ESTUDIANTE).obtener_historia(
                self.patient_id
            )[0]
        )
        self.assertFalse(
            self.history("admin", ADMIN).obtener_historia(self.patient_id)[0]
        )
        self.assertFalse(
            self.history("recepcion", RECEPCIONISTA).obtener_historia(
                self.patient_id
            )[0]
        )

        followup = CitasService("recepcion", RECEPCIONISTA, self.db_path)
        self.assertTrue(
            followup.agendar_cita(
                "doctor_two",
                self.patient_id,
                self.future,
                "10:00",
                "Cardiologia",
            )[0]
        )
        success, _, continued = self.history(
            "doctor_two",
            MEDICO,
        ).obtener_historia(self.patient_id)
        self.assertTrue(success)
        self.assertEqual(len(continued["evoluciones"]), 1)

    def test_student_cannot_read_before_attended(self):
        student = self.history("student_one", ESTUDIANTE)
        self.assertFalse(student.obtener_historia(self.patient_id)[0])
        self.assertEqual(student.listar_historias(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
