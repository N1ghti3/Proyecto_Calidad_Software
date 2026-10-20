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
import uuid

from pydantic import Field

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
