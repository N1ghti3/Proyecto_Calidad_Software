"""Modelos del catálogo y del inventario.

Corresponden uno a uno con las tablas descritas en
`docs/arquitectura/modelo-relacional.md`. Si algo difiere entre ese documento y
este archivo, el documento es el que manda y este archivo es el que está mal.
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Todas las fechas se almacenan con zona horaria y en UTC (convención del
# contrato de integración). `timezone=True` es lo que produce `timestamptz`.
MARCA_TIEMPO = DateTime(timezone=True)

# La generación de claves la hace el motor. Se usa gen_random_uuid(), nativo
# desde PostgreSQL 13, de modo que no se instala pgcrypto (ADR-009).
UUID_NUEVO = text("gen_random_uuid()")


class Category(Base):
    """Agrupación de productos para el filtro del catálogo (REQ-01)."""

    __tablename__ = "category"
    __table_args__ = (
        CheckConstraint("length(name) >= 2", name="nombre_minimo"),
        CheckConstraint(r"slug ~ '^[a-z0-9-]+$'", name="slug_formato"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=UUID_NUEVO
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(90), nullable=False, unique=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        MARCA_TIEMPO, nullable=False, server_default=text("now()")
    )


class SizeCatalog(Base):
    """Catálogo de tallas ofrecidas (ADR-008).

    Existe para que el filtro por talla pueda validarse: sin catálogo,
    `GET /products?size=XXXL` devolvería una página vacía en lugar del
    VALIDATION_ERROR que exigen las convenciones de la API.
    """

    __tablename__ = "size_catalog"
    __table_args__ = (
        CheckConstraint("code = upper(code)", name="codigo_mayusculas"),
        CheckConstraint("length(trim(label)) > 0", name="etiqueta_no_vacia"),
        CheckConstraint("position >= 0", name="posicion_no_negativa"),
    )

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    label: Mapped[str] = mapped_column(String(40), nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        MARCA_TIEMPO, nullable=False, server_default=text("now()")
    )


class Product(Base):
    """Artículo ofrecido y su estado de publicación (REQ-01, REQ-06).

    El precio vive aquí y no en la variante: el PDF no contempla precios
    distintos por talla. Cambiarlo sería un cambio de contrato.
    """

    __tablename__ = "product"
    __table_args__ = (
        CheckConstraint("length(name) >= 3", name="nombre_minimo"),
        CheckConstraint(r"slug ~ '^[a-z0-9-]+$'", name="slug_formato"),
        CheckConstraint(
            "description IS NULL OR length(description) <= 2000",
            name="descripcion_maxima",
        ),
        CheckConstraint("price_cop > 0", name="precio_positivo"),
        Index("ix_product_category_id", "category_id"),
        Index("ix_product_published", "published"),
        # Índice GIN de trigramas para la búsqueda sin distinción de mayúsculas
        # ni tildes de CA-01-2. El nombre lo fija ADR-009. Depende de la función
        # f_unaccent(), que la migración inicial crea antes de las tablas:
        # SQLAlchemy no puede garantizar ese orden y la migración sí.
        # La clase de operador va en postgresql_ops y no dentro de la
        # expresión. Escrita dentro, SQLAlchemy no puede comparar el índice y
        # `alembic check` lo da por igual sin comprobarlo: un índice que
        # desapareciera del esquema real no se notaría.
        Index(
            "idx_product_name_search",
            text("lower(f_unaccent(name))"),
            postgresql_using="gin",
            postgresql_ops={"lower(f_unaccent(name))": "gin_trgm_ops"},
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=UUID_NUEVO
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("category.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Pesos colombianos enteros: el dinero nunca se guarda en coma flotante.
    price_cop: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Por omisión un producto nace oculto: publicarlo es un acto explícito (RN-01).
    published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        MARCA_TIEMPO, nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        MARCA_TIEMPO, nullable=False, server_default=text("now()")
    )


class ProductVariant(Base):
    """Unidad vendible: un producto en una talla concreta (RN-05)."""

    __tablename__ = "product_variant"
    __table_args__ = (
        CheckConstraint(r"sku ~ '^[A-Z0-9-]+$'", name="sku_formato"),
        # Una talla no se repite dentro del mismo producto (CP-55).
        UniqueConstraint("product_id", "size", name="uq_product_variant_product_id_size"),
        Index("ix_product_variant_product_id", "product_id"),
        Index("ix_product_variant_size", "size"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=UUID_NUEVO
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sku: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    # La clave foránea garantiza que la talla exista. Que además esté activa lo
    # valida la capa de servicio: es una regla de negocio y ADR-001 no admite
    # reglas de negocio en el motor.
    size: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("size_catalog.code", ondelete="RESTRICT"),
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        MARCA_TIEMPO, nullable=False, server_default=text("now()")
    )


class Inventory(Base):
    """Existencias por variante. Fuente única de verdad del proyecto.

    Estas son las filas que se bloquean durante la confirmación de la orden
    (RN-10, ADR-005) y las que la prueba de concurrencia de RNF-02 pone a
    prueba con cincuenta solicitudes simultáneas.
    """

    __tablename__ = "inventory"
    __table_args__ = (
        # Última línea de defensa de RN-09: aunque la lógica de negocio
        # fallara, el motor rechaza el inventario negativo.
        CheckConstraint("stock_quantity >= 0", name="stock_no_negativo"),
    )

    # Clave primaria y foránea a la vez: la relación con la variante es 1:1.
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variant.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    stock_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        MARCA_TIEMPO, nullable=False, server_default=text("now()")
    )


class ProductImage(Base):
    """Imagen optimizada del catálogo (componente C5, RNF-01)."""

    __tablename__ = "product_image"
    __table_args__ = (
        CheckConstraint("length(trim(url)) > 0", name="url_no_vacia"),
        CheckConstraint("length(trim(alt_text)) > 0", name="alt_text_no_vacio"),
        CheckConstraint("position >= 0", name="posicion_no_negativa"),
        CheckConstraint("width > 0", name="ancho_positivo"),
        CheckConstraint("height > 0", name="alto_positivo"),
        UniqueConstraint(
            "product_id", "position", name="uq_product_image_product_id_position"
        ),
        Index("ix_product_image_product_id", "product_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=UUID_NUEVO
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        # Las imágenes no son histórico: si el producto se borra, se van con él.
        ForeignKey("product.id", ondelete="CASCADE"),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    # Obligatorio por RNF-03: la accesibilidad no puede depender de la buena
    # voluntad de quien carga el producto.
    alt_text: Mapped[str] = mapped_column(String(160), nullable=False)
    position: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    # Se almacenan porque el contrato los declara obligatorios: el frontend los
    # necesita para reservar el espacio de la imagen y evitar saltos de
    # diseño (RNF-01). Se conocen al cargar, porque RN-22 obliga a
    # redimensionar en el servidor.
    width: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    height: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        MARCA_TIEMPO, nullable=False, server_default=text("now()")
    )
