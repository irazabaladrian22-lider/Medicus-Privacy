"""In-memory authenticated session model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UserSession:
    user_id: int
    username: str
    name: str
    role: str

    @classmethod
    def from_auth_data(cls, data):
        return cls(
            user_id=int(data["user_id"]),
            username=str(data["usuario"]),
            name=str(data["nombre"]),
            role=str(data["rol"]),
        )
