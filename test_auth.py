import unittest
from pathlib import Path

from medicus_privacy.modules.admin import AdminService
from medicus_privacy.modules.auth import AuthService
from medicus_privacy.modules.roles import ADMIN, MEDICO


class AuthIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = Path(__file__).resolve().parent / ".test_auth.db"

    @classmethod
    def tearDownClass(cls):
        cls.db_path.unlink(missing_ok=True)

    def setUp(self):
        self.db_path.unlink(missing_ok=True)

    def test_admin_created_user_can_log_in(self):
        admin = AdminService(ADMIN, self.db_path)
        success, message = admin.crear_usuario(
            "nuevo_medico",
            "Medico123",
            MEDICO,
            "Nuevo Medico",
            "Odontologia",
        )
        self.assertTrue(success, message)
        success, role, data = AuthService(self.db_path).verificar_credenciales(
            "nuevo_medico",
            "Medico123",
        )
        self.assertTrue(success)
        self.assertEqual(role, MEDICO)
        self.assertEqual(data["usuario"], "nuevo_medico")

    def test_invalid_password_and_inactive_user_are_rejected(self):
        auth = AuthService(self.db_path)
        self.assertFalse(auth.verificar_credenciales("admin", "incorrecta")[0])
        admin = AdminService(ADMIN, self.db_path)
        admin.crear_usuario(
            "usuario_inactivo",
            "Password123",
            MEDICO,
            "Inactivo",
            "Medicina Interna",
        )
        admin.eliminar_usuario("usuario_inactivo")
        self.assertFalse(
            auth.verificar_credenciales(
                "usuario_inactivo",
                "Password123",
            )[0]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
