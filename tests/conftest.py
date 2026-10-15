"""Fixtures compartidas.

Las pruebas unitarias no necesitan nada de esto. Las de integración y las de
concurrencia necesitan un PostgreSQL 16 real, indicado por la variable
`TEST_DATABASE_ADMIN_URL`: una conexión con permiso para crear bases.

Sin esa variable las pruebas de base de datos **se omiten con un aviso**, no
fallan, de modo que las unitarias pueden ejecutarse en cualquier equipo. En el
canal de integración continua la variable siempre está definida.

Nunca se usa la base de desarrollo: cada sesión crea su propia base, la migra
desde cero con Alembic y la borra al terminar.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

import psycopg
import pytest

from apoyo import BaseDePrueba, base_efimera, conectar

VARIABLE_CLUSTER = "TEST_DATABASE_ADMIN_URL"
CARPETAS_CON_BASE = ("integration", "concurrency")


def pytest_configure(config: pytest.Config) -> None:
    # La migración inicial crea el rol de la aplicación con esta contraseña.
    # Se fija aquí para que nunca se tome del .env de quien ejecuta las pruebas.
    os.environ["APP_DB_PASSWORD"] = os.getenv("TEST_APP_DB_PASSWORD", "pruebas_app")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Marca por carpeta y omite las pruebas de base si no hay clúster."""
    hay_cluster = bool(os.getenv(VARIABLE_CLUSTER))
    omitir = pytest.mark.skip(
        reason=f"Sin {VARIABLE_CLUSTER}: ver tests/README.md para levantar PostgreSQL"
    )
    for item in items:
        partes = Path(str(item.fspath)).parts
        if "integration" in partes:
            item.add_marker(pytest.mark.integracion)
        if "concurrency" in partes:
            item.add_marker(pytest.mark.concurrencia)
        if any(c in partes for c in CARPETAS_CON_BASE) and not hay_cluster:
            item.add_marker(omitir)


@pytest.fixture(scope="session")
def url_cluster() -> str:
    return os.environ[VARIABLE_CLUSTER]


@pytest.fixture(scope="session")
def contrasena_app() -> str:
    return os.environ["APP_DB_PASSWORD"]


@pytest.fixture(scope="session")
def base_sesion(url_cluster: str, contrasena_app: str) -> Iterator[BaseDePrueba]:
    """Una base migrada a `head`, compartida por toda la sesión."""
    with base_efimera(url_cluster, contrasena_app) as base:
        yield base


@pytest.fixture
def bd(base_sesion: BaseDePrueba) -> Iterator[psycopg.Connection]:
    """Conexión con el ROL DE LA APLICACIÓN, revertida al terminar la prueba.

    Se usa el rol de la aplicación y no el propietario porque es con el que
    correrá el sistema: si una restricción solo se cumpliera para el
    propietario, no protegería nada.
    """
    with conectar(base_sesion.url_app) as conn:
        try:
            yield conn
        finally:
            conn.rollback()


@pytest.fixture
def bd_owner(base_sesion: BaseDePrueba) -> Iterator[psycopg.Connection]:
    """Conexión con el rol propietario, revertida al terminar la prueba."""
    with conectar(base_sesion.url_owner) as conn:
        try:
            yield conn
        finally:
            conn.rollback()


@pytest.fixture
def nueva_base(url_cluster: str, contrasena_app: str):
    """Fábrica de bases efímeras para pruebas que necesitan una base propia.

    Uso: `with nueva_base(migrada=False) as base: ...`
    """
    def _crear(migrada: bool = True):
        return base_efimera(url_cluster, contrasena_app, migrada=migrada)

    return _crear
