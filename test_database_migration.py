import sqlite3
import unittest
from contextlib import closing
from pathlib import Path

from medicus_privacy.modules.database import init_db
from medicus_privacy.modules.seguridad import hash_password


class DatabaseMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = Path(__file__).resolve().parent / ".test_migration.db"

    @classmethod
    def tearDownClass(cls):
        cls.db_path.unlink(missing_ok=True)

    def setUp(self):
        self.db_path.unlink(missing_ok=True)
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.executescript(
                """
                CREATE TABLE usuarios (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE,
                    password_hash TEXT,
                    rol TEXT,
                    nombre_completo TEXT,
                    activo INTEGER DEFAULT 1,
                    creado_en TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE citas (
                    id INTEGER PRIMARY KEY,
                    medico_id INTEGER,
                    estudiante_id INTEGER,
                    fecha TEXT,
                    hora TEXT,
                    especialidad TEXT,
                    motivo TEXT DEFAULT '',
                    cifrado INTEGER DEFAULT 0,
                    estado TEXT DEFAULT 'Programada',
                    creado_en TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            connection.execute(
                """
                INSERT INTO usuarios
                VALUES (1,'doctor',?,'Medico','Doctor Legacy',1,CURRENT_TIMESTAMP)
                """,
                (hash_password("Password123"),),
            )
            connection.execute(
                """
                INSERT INTO usuarios
                VALUES (2,'student',?,'Estudiante','Paciente Legacy',1,CURRENT_TIMESTAMP)
                """,
                (hash_password("Password123"),),
            )
            connection.execute(
                """
                INSERT INTO citas
                VALUES (
                    9,1,2,'2030-01-01','09:00','Cardiologia',
                    'token-legacy',1,'Programada',CURRENT_TIMESTAMP
                )
                """
            )
            connection.commit()

    def test_v1_is_migrated_without_data_loss(self):
        init_db(self.db_path, migrate_legacy=False)
        with closing(sqlite3.connect(self.db_path)) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 2)
            patient = connection.execute(
                "SELECT cedula,nombres,datos_completos FROM pacientes"
            ).fetchone()
            appointment = connection.execute(
                """
                SELECT id,paciente_id,estudiante_id,motivo_legacy
                FROM citas
                """
            ).fetchone()
            specialty = connection.execute(
                "SELECT especialidad FROM usuarios WHERE username='doctor'"
            ).fetchone()[0]
            indexes = {
                row[1]
                for row in connection.execute("PRAGMA index_list(citas)")
            }
        self.assertIn("uq_cita_medico_horario_activo", indexes)
        self.assertIn("uq_cita_paciente_horario_activo", indexes)
        self.assertEqual(patient, ("LEGACY-2", "Paciente Legacy", 0))
        self.assertEqual(appointment, (9, 1, None, "token-legacy"))
        self.assertEqual(specialty, "Medicina Interna")


if __name__ == "__main__":
    unittest.main(verbosity=2)
