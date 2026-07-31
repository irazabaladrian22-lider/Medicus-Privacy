import unittest
from pathlib import Path

from medicus_privacy.modules.admin import AdminService
from medicus_privacy.modules.roles import ADMIN, ESTUDIANTE, MEDICO


class AdminTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = Path(__file__).resolve().parent / ".test_admin.db"

    @classmethod
    def tearDownClass(cls):
        cls.db_path.unlink(missing_ok=True)

    def setUp(self):
        self.db_path.unlink(missing_ok=True)
        self.service = AdminService(ADMIN, self.db_path)

    def test_create_edit_status_and_no_password_exposure(self):
        success, message = self.service.crear_usuario(
            "doctor_test",
            "Medico123",
            MEDICO,
            "Doctor Test",
            "Cardiologia",
        )
        self.assertTrue(success, message)
        doctor = next(
            user
            for user in self.service.listar_usuarios()
            if user["username"] == "doctor_test"
        )
        self.assertNotIn("password_hash", doctor)
        self.assertEqual(doctor["especialidad"], "Cardiologia")

        success, message = self.service.actualizar_usuario(
            "doctor_test",
            "Doctor Editado",
            ESTUDIANTE,
            "Pediatria",
        )
        self.assertTrue(success, message)
        edited = next(
            user
            for user in self.service.listar_usuarios()
            if user["username"] == "doctor_test"
        )
        self.assertEqual(edited["nombre_completo"], "Doctor Editado")
        self.assertEqual(edited["rol"], ESTUDIANTE)
        self.assertEqual(edited["especialidad"], "Pediatria")

        self.assertTrue(self.service.eliminar_usuario("doctor_test")[0])
        self.assertTrue(self.service.activar_usuario("doctor_test")[0])

    def test_clinical_roles_require_specialty(self):
        success, _ = self.service.crear_usuario(
            "doctor_test",
            "Medico123",
            MEDICO,
            "Doctor Test",
        )
        self.assertFalse(success)
        success, _ = self.service.crear_usuario(
            "doctor_test",
            "Medico123",
            MEDICO,
            "Doctor Test",
            "Especialidad inventada",
        )
        self.assertFalse(success)

    def test_cannot_demote_or_remove_last_admin(self):
        success, _ = self.service.actualizar_usuario(
            "admin",
            "Admin Sistema",
            ESTUDIANTE,
            "Medicina Interna",
        )
        self.assertFalse(success)
        self.assertFalse(self.service.eliminar_usuario("admin")[0])

    def test_non_admin_is_rejected(self):
        service = AdminService(ESTUDIANTE, self.db_path)
        success, _ = service.crear_usuario(
            "intruso",
            "Password123",
            MEDICO,
            "Sin Permiso",
            "Cardiologia",
        )
        self.assertFalse(success)
        self.assertEqual(service.listar_usuarios(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
