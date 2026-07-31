import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from medicus_privacy.modules.admin import AdminService
from medicus_privacy.modules.citas import CitasService
from medicus_privacy.modules.patients import PatientService
from medicus_privacy.modules.roles import (
    ADMIN,
    ESTUDIANTE,
    MEDICO,
    RECEPCIONISTA,
)


class CitasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = Path(__file__).resolve().parent / ".test_citas.db"

    @classmethod
    def tearDownClass(cls):
        cls.db_path.unlink(missing_ok=True)

    def setUp(self):
        self.db_path.unlink(missing_ok=True)
        admin = AdminService(ADMIN, self.db_path)
        admin.crear_usuario(
            "doctor_test",
            "Medico123",
            MEDICO,
            "Doctor Test",
            "Cardiologia",
        )
        admin.crear_usuario(
            "alumno_test",
            "Alumno123",
            ESTUDIANTE,
            "Alumno Test",
            "Cardiologia",
        )
        admin.crear_usuario(
            "otro_doctor",
            "Medico456",
            MEDICO,
            "Otro Doctor",
            "Pediatria",
        )
        patients = PatientService("admin", ADMIN, self.db_path)
        self.patient_id = patients.registrar_paciente(
            "V-12345678",
            "Ana",
            "Perez",
            "2000-01-01",
            "Femenino",
        )[2]
        self.other_patient_id = patients.registrar_paciente(
            "V-87654321",
            "Luis",
            "Diaz",
            "1995-02-02",
            "Masculino",
        )[2]
        self.future = (date.today() + timedelta(days=10)).isoformat()
        self.reception = CitasService(
            "recepcion",
            RECEPCIONISTA,
            self.db_path,
        )

    def test_schedule_filters_staff_and_prevents_collisions(self):
        success, message = self.reception.agendar_cita(
            "doctor_test",
            self.patient_id,
            self.future,
            "09:00",
            "Cardiologia",
            "alumno_test",
        )
        self.assertTrue(success, message)
        self.assertFalse(
            self.reception.verificar_disponibilidad(
                "doctor_test",
                self.future,
                "09:00",
            )
        )
        self.assertFalse(
            self.reception.agendar_cita(
                "doctor_test",
                self.other_patient_id,
                self.future,
                "09:00",
                "Cardiologia",
            )[0]
        )
        self.assertFalse(
            self.reception.agendar_cita(
                "otro_doctor",
                self.other_patient_id,
                self.future,
                "10:00",
                "Cardiologia",
            )[0]
        )

    def test_role_views_and_cancellation(self):
        self.assertTrue(
            self.reception.agendar_cita(
                "doctor_test",
                self.patient_id,
                self.future,
                "10:00",
                "Cardiologia",
                "alumno_test",
            )[0]
        )
        appointment_id = self.reception.obtener_citas()[0]["id"]
        student = CitasService("alumno_test", ESTUDIANTE, self.db_path)
        self.assertEqual(len(student.obtener_citas()), 1)
        self.assertFalse(student.cancelar_cita(appointment_id)[0])

        other_doctor = CitasService("otro_doctor", MEDICO, self.db_path)
        self.assertFalse(other_doctor.cancelar_cita(appointment_id)[0])
        doctor = CitasService("doctor_test", MEDICO, self.db_path)
        self.assertTrue(doctor.cancelar_cita(appointment_id)[0])

    def test_doctor_only_schedules_self_and_past_is_rejected(self):
        doctor = CitasService("doctor_test", MEDICO, self.db_path)
        self.assertFalse(
            doctor.agendar_cita(
                "otro_doctor",
                self.patient_id,
                self.future,
                "11:00",
                "Pediatria",
            )[0]
        )
        past = (date.today() - timedelta(days=1)).isoformat()
        self.assertFalse(
            self.reception.agendar_cita(
                "doctor_test",
                self.patient_id,
                past,
                "11:00",
                "Cardiologia",
            )[0]
        )
        valid, _ = CitasService.validar_fecha_hora(
            self.future,
            "11:15",
            now=datetime.now(),
        )
        self.assertFalse(valid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
