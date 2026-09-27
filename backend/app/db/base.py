"""Base declarativa de SQLAlchemy y convención de nombres de restricciones.

La convención de nombres importa más de lo que parece. Sin ella, PostgreSQL
inventa nombres para las restricciones y los índices, Alembic no puede
referirse a ellos al revertir una migración, y una restricción que falla
produce un mensaje de error que no dice qué regla se violó.

Con ella, `ck_inventory_stock_no_negativo` se lee solo: la tabla, el tipo de
restricción y la regla. Eso es lo que aparece en el error cuando RN-09 se
intenta violar, y es lo que una prueba puede afirmar.

Los prefijos son los habituales: `pk` clave primaria, `fk` clave foránea,
`uq` restricción de unicidad, `ck` restricción de verificación, `ix` índice.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

CONVENCION_NOMBRES = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Clase base de todos los modelos de TiendaLocal."""

    metadata = MetaData(naming_convention=CONVENCION_NOMBRES)
