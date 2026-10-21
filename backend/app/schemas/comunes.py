"""Piezas compartidas por todos los esquemas de la API.

Dos decisiones del contrato se concentran aquí para que ningún esquema tenga
que recordarlas:

1. **camelCase en el JSON, snake_case en Python** (ADR-003). La conversión la
   hace el alias generado, de modo que los modelos de SQLAlchemy conservan sus
   nombres y el JSON conserva los suyos. Nadie escribe la traducción a mano.

2. **Las colecciones viajan envueltas en `Page<T>`** (convenciones.md). Nunca
   como lista desnuda: una lista sin metadatos obliga al cliente a adivinar si
   hay más páginas, y el frontend necesita saberlo para recorrer el catálogo.
"""

from __future__ import annotations

import math
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class ModeloApi(BaseModel):
    """Base de todo esquema que entra o sale por la API.

    `populate_by_name` permite construir el objeto en Python con los nombres
    snake_case y serializarlo en camelCase sin duplicar definiciones.

    `extra="forbid"` cumple la regla 3 de convenciones.md: un campo desconocido
    se rechaza con VALIDATION_ERROR. Sin ella, un `availableUnits` enviado
    donde se esperaba `stockQuantity` se ignoraba en silencio y el error de
    nombre entre frontend y backend no aparecía hasta producción.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        extra="forbid",
    )


class MetaPagina(ModeloApi):
    """Metadatos de paginación. `totalPages` se deriva, nunca se recibe."""

    page: int
    page_size: int
    total_items: int
    total_pages: int


class Pagina(ModeloApi, Generic[T]):
    """Envoltorio de toda colección paginada."""

    items: list[T]
    meta: MetaPagina

    @classmethod
    def construir(
        cls, items: list[T], *, pagina: int, tamano: int, total: int
    ) -> "Pagina[T]":
        return cls(
            items=items,
            meta=MetaPagina(
                page=pagina,
                page_size=tamano,
                total_items=total,
                total_pages=max(1, math.ceil(total / tamano)) if tamano else 1,
            ),
        )
