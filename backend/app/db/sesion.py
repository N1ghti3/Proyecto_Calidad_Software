"""Motor y sesiones de SQLAlchemy para la aplicación en ejecución.

Se conecta con `DATABASE_URL`, es decir con el rol `tiendalocal_app`, que por
ADR-010 **no puede actualizar ni borrar `audit_log`**. Esa restricción no es
decorativa: es lo que hace que la auditoría sea de solo anexado aunque la
aplicación tenga un defecto. Arrancar con el rol propietario la anularía sin
que nadie se entere, y por eso la configuración mantiene las dos cadenas
separadas y ninguna tiene valor por omisión.

`expire_on_commit=False` permite leer los objetos después de confirmar la
transacción. Sin eso, serializar una orden recién creada dispararía una consulta
nueva por cada atributo, fuera ya de la transacción que la creó.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import obtener_settings

_settings = obtener_settings()

motor = create_engine(
    _settings.database_url,
    # Comprueba la conexión antes de usarla: tras un reinicio del contenedor de
    # PostgreSQL las conexiones del pool quedan muertas y el primer uso falla.
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=5,
    future=True,
)

FabricaSesion = sessionmaker(
    bind=motor, autoflush=False, autocommit=False, expire_on_commit=False
)


def obtener_sesion() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión por petición, siempre cerrada.

    No confirma por su cuenta. Cada ruta decide cuándo hacerlo, porque la
    frontera de la transacción es una decisión de negocio y no de infraestructura
    —y en el caso de la creación de órdenes es *la* decisión del proyecto.
    """
    sesion = FabricaSesion()
    try:
        yield sesion
    finally:
        sesion.close()
