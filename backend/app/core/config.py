"""Configuración leída del entorno.

Ninguna credencial vive en el código ni en un archivo versionado: todo sale del
archivo `.env` de la raíz del repositorio, creado a partir de `.env.example` y
excluido por `.gitignore` (riesgo R-07, RNF-04).

ADR-010 establece dos roles de base de datos con privilegios distintos, y por
eso hay dos cadenas de conexión:

- ``database_url``            → rol ``tiendalocal_app``, con el que corre la
                                aplicación. No puede actualizar ni borrar
                                ``audit_log``.
- ``database_migration_url``  → rol ``tiendalocal_owner``, con el que corre
                                Alembic. Crea tablas y extensiones.

Que la aplicación arranque con el rol propietario anularía la protección de la
auditoría sin aviso, de modo que son dos campos separados y ninguno tiene valor
por omisión.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> backend/app/core -> backend/app -> backend -> raíz
RAIZ_REPOSITORIO = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Variables de entorno del backend."""

    model_config = SettingsConfigDict(
        env_file=RAIZ_REPOSITORIO / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Conexión de la aplicación en ejecución (rol tiendalocal_app).
    database_url: str

    # Conexión de las migraciones (rol tiendalocal_owner).
    database_migration_url: str

    # Contraseña del rol de la aplicación. La migración inicial la necesita
    # para crear ese rol; después de eso, nada más la usa.
    app_db_password: str


@lru_cache
def obtener_settings() -> Settings:
    """Devuelve la configuración, leída una sola vez por proceso."""
    return Settings()  # type: ignore[call-arg]
