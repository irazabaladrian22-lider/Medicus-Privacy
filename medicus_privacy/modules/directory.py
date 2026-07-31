"""Read-only clinical staff directory."""

from medicus_privacy.modules.catalogs import normalize_specialty
from medicus_privacy.modules.database import DatabaseService
from medicus_privacy.modules.roles import (
    ADMIN,
    ESTUDIANTE,
    MEDICO,
    RECEPCIONISTA,
    normalizar_rol,
)


class DirectoryService:
    def __init__(self, actor_role, db_path=None):
        self.actor_role = normalizar_rol(actor_role)
        self.database = DatabaseService(db_path)

    def listar_medicos(self, especialidad=None):
        if self.actor_role not in (ADMIN, RECEPCIONISTA, MEDICO):
            return []
        return self._list_by_role(MEDICO, especialidad)

    def listar_estudiantes(self, especialidad=None):
        if self.actor_role not in (ADMIN, RECEPCIONISTA):
            return []
        return self._list_by_role(ESTUDIANTE, especialidad)

    def _list_by_role(self, role, specialty):
        clauses = ["rol = ?", "activo = 1"]
        params = [role]
        if specialty:
            normalized = normalize_specialty(specialty)
            if not normalized:
                return []
            clauses.append("especialidad = ?")
            params.append(normalized)
        with self.database.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT username, nombre_completo, especialidad
                FROM usuarios
                WHERE {' AND '.join(clauses)}
                ORDER BY nombre_completo, username
                """,
                params,
            ).fetchall()
        return [dict(row) for row in rows]
