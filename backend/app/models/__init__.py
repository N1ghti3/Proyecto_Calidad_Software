"""Modelos de datos de TiendaLocal.

Importar este paquete registra las once tablas en `Base.metadata`. De eso
depende que `alembic revision --autogenerate` pueda comparar los modelos contra
el esquema real: un modelo que no se importa aquí es invisible para Alembic, y
Alembic propondría borrar su tabla.
"""

from app.db.base import Base
from app.models.administracion import AdminUser, AuditLog
from app.models.catalogo import (
    Category,
    Inventory,
    Product,
    ProductImage,
    ProductVariant,
    SizeCatalog,
)
from app.models.ordenes import Notification, OrderHeader, OrderItem

__all__ = [
    "Base",
    # Catálogo e inventario
    "Category",
    "SizeCatalog",
    "Product",
    "ProductVariant",
    "Inventory",
    "ProductImage",
    # Órdenes
    "OrderHeader",
    "OrderItem",
    "Notification",
    # Administración y auditoría
    "AdminUser",
    "AuditLog",
]
