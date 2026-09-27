"""Entorno de ejecución de Alembic.

Dos cosas que este archivo hace a propósito:

1. **La URL no está en `alembic.ini`.** Se lee de `DATABASE_MIGRATION_URL`, que
   apunta al rol propietario. Escribirla en el archivo de configuración la
   versionaría (riesgo R-07).
2. **Compara tipos y valores por omisión.** Sin `compare_type` y
   `compare_server_default`, un `varchar(80)` que pasó a `varchar(120)` en el
   modelo no aparece en la autogeneración y el esquema real queda divergiendo en
   silencio, que es justo lo que ADR-009 descarta al rechazar `create_all()`.

Recordatorio de ADR-009: la autogeneración **se revisa a mano**. Detecta bien
las adiciones y mal los renombrados, que interpreta como borrar y crear. No
detecta los índices por expresión (los de `lower(...)` y `DESC`), de modo que
esos se escriben en la revisión y no se esperan de la comparación.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Permite `python -m alembic` desde backend/ sin instalar el paquete.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import Base  # noqa: E402
import app.models  # noqa: F401,E402  (registra las once tablas en Base.metadata)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url_de_migracion() -> str:
    """URL del rol propietario, tomada del entorno.

    Se acepta también `-x url=...` en la línea de comandos, que es lo que usa el
    canal de integración continua para apuntar a la base efímera de la prueba
    sin escribir un `.env`.
    """
    argumentos = context.get_x_argument(as_dictionary=True)
    url = argumentos.get("url") or os.getenv("DATABASE_MIGRATION_URL")

    if not url:
        # Último recurso: el archivo .env de la raíz del repositorio.
        try:
            from app.core.config import obtener_settings

            url = obtener_settings().database_migration_url
        except Exception:  # pragma: no cover - solo mejora el mensaje de error
            url = None

    if not url:
        raise RuntimeError(
            "Falta DATABASE_MIGRATION_URL. Copia .env.example como .env en la "
            "raíz del repositorio y rellena las credenciales, o pasa la URL con "
            "'alembic -x url=postgresql+psycopg://...'."
        )
    return url


def migrar_sin_conexion() -> None:
    """Modo 'offline': emite el SQL por salida estándar, sin tocar la base.

    Sirve para revisar en un Pull Request qué va a ejecutarse antes de
    ejecutarlo.
    """
    context.configure(
        url=_url_de_migracion(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def migrar_con_conexion() -> None:
    """Modo normal: aplica las migraciones contra la base configurada."""
    seccion = config.get_section(config.config_ini_section, {})
    seccion["sqlalchemy.url"] = _url_de_migracion()

    motor = engine_from_config(seccion, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with motor.connect() as conexion:
        context.configure(
            connection=conexion,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    motor.dispose()


if context.is_offline_mode():
    migrar_sin_conexion()
else:
    migrar_con_conexion()
