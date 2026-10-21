"""Esquemas del catálogo público, según `docs/api/modelos.md`.

Nota sobre `availableUnits` en el resumen: es la suma de existencias de todas
las variantes del producto, y sirve para decidir si la tarjeta se muestra como
disponible. **No alcanza para comprar.** El resumen trae los nombres de las
tallas pero no sus identificadores, de modo que agregar al carrito desde el
catálogo obliga a pedir el detalle (EP-03). Es deliberado: se compra por
variante y nunca por producto (RN-05), y un carrito que guardara el
identificador del producto no sabría qué talla descontar.
"""

from __future__ import annotations

import datetime
import re
import uuid

from pydantic import Field, field_validator

from app.schemas.comunes import ModeloApi


class CategoryResponse(ModeloApi):
    id: uuid.UUID
    name: str
    slug: str
    # Cuenta solo productos publicados: el filtro no debe prometer resultados
    # que el catálogo público no va a mostrar.
    product_count: int = 0


class ProductImageResponse(ModeloApi):
    id: uuid.UUID
    url: str
    alt: str | None = None
    position: int = 0
    # Para que el navegador reserve el espacio antes de que llegue la imagen
    # y la página no salte al cargarla (modelos.md, RNF-01).
    width: int | None = None
    height: int | None = None


class ProductVariantResponse(ModeloApi):
    id: uuid.UUID
    sku: str
    size: str
    available_units: int
    in_stock: bool


class ProductSummaryResponse(ModeloApi):
    id: uuid.UUID
    slug: str
    name: str
    price_cop: int
    category_name: str
    image_url: str | None = None
    image_alt: str | None = None
    available_units: int
    in_stock: bool
    sizes: list[str] = Field(default_factory=list)


class AdminProductSummaryResponse(ProductSummaryResponse):
    """Igual que el resumen público, más el estado de publicación.

    Es un esquema aparte y no un campo opcional del público porque en el
    catálogo abierto todo lo devuelto está publicado por definición: incluir
    `published` allí sería un campo que siempre vale lo mismo, o peor, un
    `null` que el cliente tiene que aprender a ignorar.
    """

    published: bool


class ProductResponse(ProductSummaryResponse):
    description: str | None = None
    category: CategoryResponse
    images: list[ProductImageResponse] = Field(default_factory=list)
    variants: list[ProductVariantResponse] = Field(default_factory=list)
    # Siempre `true` en el detalle público (modelos.md); en el panel (EP-22,
    # EP-25) dice si el producto está a la vista.
    published: bool = True
    updated_at: datetime.datetime | None = None


# ------------------------------------------------- alta y edición (panel)

# Mismo formato que exige `ck_product_variant_sku_formato`: comprobarlo aquí
# convierte el error de la base en un VALIDATION_ERROR legible.
_SKU = re.compile(r"^[A-Z0-9-]+$")


class VariantRequest(ModeloApi):
    """EP-12 y EP-14. La talla debe existir en `size_catalog` (ADR-008); eso
    se comprueba contra la base en el servicio, no aquí."""

    size: str = Field(min_length=1, max_length=20)
    sku: str | None = Field(default=None, max_length=40)
    initial_stock: int = Field(ge=0)
    active: bool = True

    @field_validator("size")
    @classmethod
    def _talla(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("sku")
    @classmethod
    def _sku(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        v = v.strip().upper()
        if not _SKU.match(v):
            raise ValueError("solo letras A-Z sin tilde, dígitos y guiones")
        return v


class ProductCreateRequest(ModeloApi):
    """EP-12. Un único envío con variantes y existencias iniciales (REQ-06.4)."""

    name: str = Field(min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    price_cop: int = Field(gt=0)
    category_id: uuid.UUID
    variants: list[VariantRequest] = Field(min_length=1, max_length=20)
    published: bool = False

    @field_validator("name")
    @classmethod
    def _nombre(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 3:
            raise ValueError("debe tener al menos 3 caracteres")
        return v

    @field_validator("description")
    @classmethod
    def _descripcion(cls, v: str | None) -> str | None:
        return _limpiar_descripcion(v)


def _limpiar_descripcion(v: str | None) -> str | None:
    """Una descripción en blanco es una descripción ausente."""
    if v is None:
        return None
    return v.strip() or None


class ProductUpdateRequest(ModeloApi):
    """EP-22. Todos opcionales; se aplican solo los enviados.

    `variants` no se acepta aquí (modelos.md): reemplazar la lista desde un
    formulario de edición borraría por accidente tallas con ventas. Las tallas
    nuevas entran por EP-14.
    """

    name: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    price_cop: int | None = Field(default=None, gt=0)
    category_id: uuid.UUID | None = None
    published: bool | None = None

    @field_validator("name")
    @classmethod
    def _nombre(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = " ".join(v.split())
        if len(v) < 3:
            raise ValueError("debe tener al menos 3 caracteres")
        return v

    @field_validator("description")
    @classmethod
    def _descripcion(cls, v: str | None) -> str | None:
        return _limpiar_descripcion(v)


class InventoryResponse(ModeloApi):
    """Fila de la vista de inventario (EP-24) y respuesta del ajuste (EP-15)."""

    variant_id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    sku: str
    size: str
    # `stockQuantity` y no `availableUnits`, como fija modelos.md: es el mismo
    # nombre que recibe el ajuste (EP-15), así el panel lee y escribe un campo.
    stock_quantity: int
    updated_at: datetime.datetime | None = None
    price_cop: int | None = None
    category_name: str | None = None
    image_url: str | None = None
    published: bool | None = None
    # Calculado contra `lowStockThreshold`; evita que el panel repita el umbral.
    low_stock: bool | None = None
