"""Versioned SQLite persistence and migration from the original data model."""

import json
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from medicus_privacy.modules.catalogs import SPECIALTIES
from medicus_privacy.modules.roles import (
    ADMIN,
    ESTUDIANTE,
    MEDICO,
    RECEPCIONISTA,
    normalizar_rol,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "medicus_privacy.db"
LEGACY_USERS_PATH = PROJECT_ROOT / "data" / "users.json"
LEGACY_DB_PATH = PROJECT_ROOT / "db_medicus.json"
SCHEMA_VERSION = 2


def resolve_db_path(db_path=None):
    if db_path:
        return Path(db_path).resolve()
    import os

    configured = os.environ.get("MEDICUS_DB_PATH")
    return Path(configured).resolve() if configured else DEFAULT_DB_PATH


def get_connection(db_path=None):
    path = resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


@contextmanager
def managed_connection(db_path=None):
    connection = get_connection(db_path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _table_exists(connection, table):
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def _columns(connection, table):
    if not _table_exists(connection, table):
        return set()
    return {
        row["name"] for row in connection.execute(f"PRAGMA table_info({table})")
    }


def _backup_legacy_database(path):
    if path != DEFAULT_DB_PATH or not path.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.stem}.backup-v1-{stamp}{path.suffix}")
    shutil.copy2(path, backup)
    return backup


def init_db(db_path=None, migrate_legacy=None):
    path = resolve_db_path(db_path)
    if migrate_legacy is None:
        migrate_legacy = db_path is None

    with managed_connection(path) as connection:
        has_users = _table_exists(connection, "usuarios")
        is_v1 = (
            _table_exists(connection, "citas")
            and "estudiante_id" in _columns(connection, "citas")
            and "paciente_id" not in _columns(connection, "citas")
        )

    if is_v1:
        _backup_legacy_database(path)

    with managed_connection(path) as connection:
        if is_v1:
            _migrate_v1_to_v2(connection)
        else:
            _create_schema(connection)

        if not has_users and migrate_legacy:
            _migrate_legacy_users(connection)
        if connection.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0:
            _seed_default_users(connection)
        _ensure_clinical_specialties(connection)
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    return path


def _create_schema(connection):
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL CHECK (
                rol IN ('Admin', 'Medico', 'Recepcionista', 'Estudiante')
            ),
            nombre_completo TEXT NOT NULL,
            especialidad TEXT,
            activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
            creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula TEXT NOT NULL UNIQUE COLLATE NOCASE,
            nombres TEXT NOT NULL,
            apellidos TEXT NOT NULL,
            fecha_nacimiento TEXT,
            sexo TEXT NOT NULL DEFAULT 'No especificado',
            nacionalidad TEXT NOT NULL DEFAULT '',
            direccion TEXT NOT NULL DEFAULT '',
            datos_completos INTEGER NOT NULL DEFAULT 1
                CHECK (datos_completos IN (0, 1)),
            creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS citas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medico_id INTEGER NOT NULL,
            paciente_id INTEGER NOT NULL,
            estudiante_id INTEGER,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            especialidad TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'Programada'
                CHECK (estado IN ('Programada', 'Atendida', 'Cancelada')),
            motivo_legacy TEXT NOT NULL DEFAULT '',
            motivo_legacy_cifrado INTEGER NOT NULL DEFAULT 0,
            creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (medico_id) REFERENCES usuarios(id),
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
            FOREIGN KEY (estudiante_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS historias_clinicas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL UNIQUE,
            creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            actualizado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
        );

        CREATE TABLE IF NOT EXISTS evoluciones_clinicas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            historia_id INTEGER NOT NULL,
            cita_id INTEGER NOT NULL UNIQUE,
            medico_id INTEGER NOT NULL,
            altura_cm REAL,
            peso_kg REAL,
            diagnostico_cifrado TEXT NOT NULL,
            tratamiento_cifrado TEXT NOT NULL,
            creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (historia_id) REFERENCES historias_clinicas(id),
            FOREIGN KEY (cita_id) REFERENCES citas(id),
            FOREIGN KEY (medico_id) REFERENCES usuarios(id)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS uq_cita_medico_horario_activo
            ON citas(medico_id, fecha, hora)
            WHERE estado = 'Programada';
        CREATE UNIQUE INDEX IF NOT EXISTS uq_cita_paciente_horario_activo
            ON citas(paciente_id, fecha, hora)
            WHERE estado = 'Programada';
        CREATE UNIQUE INDEX IF NOT EXISTS uq_cita_estudiante_horario_activo
            ON citas(estudiante_id, fecha, hora)
            WHERE estado = 'Programada' AND estudiante_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_citas_paciente
            ON citas(paciente_id, fecha, hora);
        CREATE INDEX IF NOT EXISTS idx_citas_estudiante
            ON citas(estudiante_id, fecha, hora);
        CREATE INDEX IF NOT EXISTS idx_evoluciones_historia
            ON evoluciones_clinicas(historia_id, creado_en);
        """
    )


def _migrate_v1_to_v2(connection):
    connection.executescript(
        """
        DROP INDEX IF EXISTS uq_cita_medico_horario_activo;
        DROP INDEX IF EXISTS uq_cita_paciente_horario_activo;
        DROP INDEX IF EXISTS uq_cita_estudiante_horario_activo;
        DROP INDEX IF EXISTS idx_citas_estudiante;
        DROP INDEX IF EXISTS idx_citas_paciente;
        """
    )
    if "especialidad" not in _columns(connection, "usuarios"):
        connection.execute("ALTER TABLE usuarios ADD COLUMN especialidad TEXT")

    connection.execute("ALTER TABLE citas RENAME TO citas_v1")
    _create_schema(connection)

    legacy_rows = connection.execute(
        """
        SELECT c.*, e.id AS legacy_user_id, e.nombre_completo AS legacy_name
        FROM citas_v1 c
        JOIN usuarios e ON e.id = c.estudiante_id
        ORDER BY c.id
        """
    ).fetchall()
    patient_ids = {}
    for row in legacy_rows:
        legacy_user_id = row["legacy_user_id"]
        if legacy_user_id not in patient_ids:
            cedula = f"LEGACY-{legacy_user_id}"
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO pacientes (
                    cedula, nombres, apellidos, fecha_nacimiento, sexo,
                    datos_completos
                ) VALUES (?, ?, 'Por completar', NULL, 'No especificado', 0)
                """,
                (cedula, row["legacy_name"]),
            )
            patient = connection.execute(
                "SELECT id FROM pacientes WHERE cedula = ?",
                (cedula,),
            ).fetchone()
            patient_ids[legacy_user_id] = patient["id"]

        connection.execute(
            """
            INSERT INTO citas (
                id, medico_id, paciente_id, estudiante_id, fecha, hora,
                especialidad, estado, motivo_legacy, motivo_legacy_cifrado,
                creado_en
            ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                row["medico_id"],
                patient_ids[legacy_user_id],
                row["fecha"],
                row["hora"],
                row["especialidad"],
                "Cancelada" if row["estado"] == "Cancelada" else "Programada",
                row["motivo"],
                row["cifrado"],
                row["creado_en"],
            ),
        )
    connection.execute("DROP TABLE citas_v1")


def _migrate_legacy_users(connection):
    sources = []
    if LEGACY_USERS_PATH.exists():
        try:
            data = json.loads(LEGACY_USERS_PATH.read_text(encoding="utf-8"))
            sources.extend(data.get("usuarios", []))
        except (OSError, json.JSONDecodeError):
            pass

    for user in sources:
        role = normalizar_rol(user.get("rol"))
        salt = user.get("salt")
        password_hash = user.get("password_hash")
        username = str(user.get("usuario", "")).strip().lower()
        if not role or not salt or not password_hash or not username:
            continue
        connection.execute(
            """
            INSERT OR IGNORE INTO usuarios (
                username, password_hash, rol, nombre_completo, activo
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                username,
                f"pbkdf2_sha256$120000${salt}${password_hash}",
                role,
                str(user.get("nombre") or username).strip(),
                1 if user.get("activo", True) else 0,
            ),
        )


def _seed_default_users(connection):
    from medicus_privacy.modules.seguridad import hash_password

    users = (
        ("admin", "admin123", ADMIN, "Admin Sistema", None),
        ("medico", "med123", MEDICO, "Dr. Garcia", SPECIALTIES[0]),
        ("recepcion", "rec123", RECEPCIONISTA, "Recepcion Principal", None),
        (
            "estudiante",
            "est123",
            ESTUDIANTE,
            "Estudiante Demo",
            SPECIALTIES[0],
        ),
    )
    connection.executemany(
        """
        INSERT INTO usuarios (
            username, password_hash, rol, nombre_completo, especialidad
        ) VALUES (?, ?, ?, ?, ?)
        """,
        [
            (username, hash_password(password), role, name, specialty)
            for username, password, role, name, specialty in users
        ],
    )


def _ensure_clinical_specialties(connection):
    default = SPECIALTIES[0]
    connection.execute(
        """
        UPDATE usuarios
        SET especialidad = ?
        WHERE rol IN ('Medico', 'Estudiante')
          AND (especialidad IS NULL OR TRIM(especialidad) = '')
        """,
        (default,),
    )
    connection.execute(
        """
        UPDATE usuarios
        SET especialidad = NULL
        WHERE rol NOT IN ('Medico', 'Estudiante')
        """
    )


class DatabaseService:
    def __init__(self, db_path=None):
        self.db_path = init_db(db_path)

    def connect(self):
        return managed_connection(self.db_path)
