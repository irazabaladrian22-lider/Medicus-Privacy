import unittest
from pathlib import Path

from medicus_privacy.gui.app import navigation_for_role
from medicus_privacy.gui.session import UserSession
from medicus_privacy.gui.widgets import TIME_SLOTS
from medicus_privacy.modules.admin import AdminService
from medicus_privacy.modules.directory import DirectoryService
from medicus_privacy.modules.roles import ADMIN, ESTUDIANTE, MEDICO, RECEPCIONISTA


class GuiSupportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = Path(__file__).resolve().parent / ".test_gui.db"

    @classmethod
    def tearDownClass(cls):
        cls.db_path.unlink(missing_ok=True)

    def setUp(self):
        self.db_path.unlink(missing_ok=True)

    def test_navigation_is_limited_by_role(self):
        self.assertEqual(
            navigation_for_role(ADMIN),
            (
                ("Usuarios", "users"),
                ("Citas", "appointments"),
                ("Pacientes", "patients"),
            ),
        )
        self.assertEqual(
            navigation_for_role(RECEPCIONISTA),
            (("Citas", "appointments"), ("Pacientes", "patients")),
        )
        for role in (MEDICO, ESTUDIANTE):
            self.assertEqual(
                navigation_for_role(role),
                (
                    ("Citas", "appointments"),
                    ("Historias clinicas", "histories"),
                ),
            )

    def test_session_and_time_slots(self):
        session = UserSession.from_auth_data(
            {
                "user_id": 7,
                "usuario": "medico",
                "nombre": "Medico Principal",
                "rol": MEDICO,
            }
        )
        self.assertEqual(session.username, "medico")
        self.assertEqual(TIME_SLOTS[0], "07:00")
        self.assertEqual(TIME_SLOTS[-1], "19:00")
        self.assertNotIn("07:15", TIME_SLOTS)

    def test_directory_filters_by_specialty_and_role(self):
        admin = AdminService(ADMIN, self.db_path)
        admin.crear_usuario(
            "doctor_gui",
            "Password123",
            MEDICO,
            "Doctor GUI",
            "Cardiologia",
        )
        admin.crear_usuario(
            "student_gui",
            "Password123",
            ESTUDIANTE,
            "Estudiante GUI",
            "Cardiologia",
        )
        reception = DirectoryService(RECEPCIONISTA, self.db_path)
        self.assertEqual(
            [item["username"] for item in reception.listar_medicos("Cardiologia")],
            ["doctor_gui"],
        )
        self.assertEqual(
            [
                item["username"]
                for item in reception.listar_estudiantes("Cardiologia")
            ],
            ["student_gui"],
        )
        self.assertEqual(
            DirectoryService(ESTUDIANTE, self.db_path).listar_estudiantes(),
            [],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
