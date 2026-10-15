"""ADR-010 — las dos cadenas de conexión son obligatorias y no tienen valor por omisión.

Si alguna tuviera un valor por omisión, la aplicación podría arrancar conectada
con el rol equivocado sin que nada avisara.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings

VARIABLES = ("DATABASE_URL", "DATABASE_MIGRATION_URL", "APP_DB_PASSWORD")


@pytest.fixture
def entorno_limpio(monkeypatch):
    for variable in VARIABLES:
        monkeypatch.delenv(variable, raising=False)
    return monkeypatch


@pytest.mark.parametrize("faltante", VARIABLES)
def test_falla_si_falta_una_variable_obligatoria(entorno_limpio, faltante):
    for variable in VARIABLES:
        if variable != faltante:
            entorno_limpio.setenv(variable, "valor")

    with pytest.raises(ValidationError) as error:
        # _env_file=None: no leer el .env de quien ejecuta la prueba.
        Settings(_env_file=None)

    assert faltante.lower() in str(error.value).lower()


def test_lee_las_dos_conexiones_por_separado(entorno_limpio):
    entorno_limpio.setenv("DATABASE_URL", "postgresql+psycopg://app@h/b")
    entorno_limpio.setenv("DATABASE_MIGRATION_URL", "postgresql+psycopg://owner@h/b")
    entorno_limpio.setenv("APP_DB_PASSWORD", "secreto")

    ajustes = Settings(_env_file=None)

    assert ajustes.database_url.endswith("app@h/b")
    assert ajustes.database_migration_url.endswith("owner@h/b")
    assert ajustes.database_url != ajustes.database_migration_url
