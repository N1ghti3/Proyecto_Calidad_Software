"""Modelos de órdenes, líneas de orden y notificaciones.

Una orden confirmada es un documento que la Ley 527 de 1999 obliga a conservar
íntegro y recuperable. De ahí vienen dos decisiones que se ven en este archivo:
las líneas guardan una copia congelada de nombre, talla y precio (RN-28), y
nada de lo que apunta al histórico admite borrado en cascada.
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
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

MARCA_TIEMPO = DateTime(timezone=True)
UUID_NUEVO = text("gen_random_uuid()")

# Formato del número público de orden (ADR-010): TL- + fecha UTC + cinco
# caracteres de un alfabeto de 32 símbolos sin 0, 1, I ni O, porque el número
# se dicta por teléfono y se transcribe a mano.
FORMATO_NUMERO_ORDEN = r"order_number ~ '^TL-[0-9]{8}-[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{5}$'"

# Verificación de correo deliberadamente laxa: el motor comprueba la forma
# mínima y la validación real vive en la capa de servicio, donde puede devolver
# un VALIDATION_ERROR con el campo señalado en lugar de un error de motor.
FORMA_CORREO = r"^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$"

ESTADOS_ORDEN = ("CONFIRMADA", "PREPARADA", "ENTREGADA", "CANCELADA")


class OrderHeader(Base):
    """Orden confirmada, datos de entrega y constancia de autorización.

    La tabla se llama `order_header` porque `order` es palabra reservada en SQL.
    El recurso de la API sigue llamándose `order`.

    Campos que deliberadamente no existen: ningún dato de tarjeta, medio de
    pago, documento de identidad, fecha de nacimiento ni geolocalización. Cada
    columna personal de las que sí existen tiene una finalidad declarada en el
    modelo relacional (RN-17, RNF-04).
    """

    __tablename__ = "order_header"
    __table_args__ = (
        CheckConstraint(FORMATO_NUMERO_ORDEN, name="numero_formato"),
        CheckConstraint(
            "status IN ('" + "', '".join(ESTADOS_ORDEN) + "')", name="estado_valido"
        ),
        CheckConstraint("total_cop > 0", name="total_positivo"),
        CheckConstraint("length(trim(customer_name)) > 0", name="nombre_no_vacio"),
        CheckConstraint(f"customer_email ~* '{FORMA_CORREO}'", name="correo_formato"),
        CheckConstraint(r"customer_phone ~ '^[0-9]{7,15}$'", name="telefono_formato"),
        CheckConstraint(
            "length(trim(shipping_address)) > 0", name="direccion_no_vacia"
        ),
        CheckConstraint("length(trim(shipping_city)) > 0", name="ciudad_no_vacia"),
        # RN-16: sin autorización expresa no hay orden. No es un valor por
        # omisión ni un campo que se pueda dejar en falso: la fila no existe.
        CheckConstraint("data_processing_consent = true", name="consentimiento_obligatorio"),
        # Listado del panel (REQ-07.1): filtra por estado y ordena por fecha
        # descendente, que es exactamente lo que este índice sirve.
        Index(
            "ix_order_header_status_created_at",
            "status",
            text("created_at DESC"),
        ),
        # Consulta del comprador (RN-18): número de orden más correo.
        Index("ix_order_header_customer_email", text("lower(customer_email)")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=UUID_NUEVO
    )
    # Se genera en la capa de servicio antes de abrir la transacción. Esta
    # restricción de unicidad es la garantía final ante una colisión (ADR-010).
    order_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'CONFIRMADA'")
    )
    total_cop: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # --- Datos personales. Finalidad declarada, mínimo necesario (RN-17) ---
    customer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(160), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    shipping_address: Mapped[str] = mapped_column(String(200), nullable=False)
    shipping_city: Mapped[str] = mapped_column(String(80), nullable=False)

    # --- Constancia de la autorización (RN-16, CA-08-2) ---
    data_processing_consent: Mapped[bool] = mapped_column(Boolean, nullable=False)
    privacy_notice_version: Mapped[str] = mapped_column(String(20), nullable=False)
    consent_at: Mapped[datetime.datetime] = mapped_column(
        MARCA_TIEMPO, nullable=False, server_default=text("now()")
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        MARCA_TIEMPO, nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        MARCA_TIEMPO, nullable=False, server_default=text("now()")
    )


class OrderItem(Base):
    """Línea de orden con copia de los datos del momento de la compra (RN-28).

    `size` no lleva clave foránea a `size_catalog` a propósito (ADR-008): es una
    copia congelada. Si apuntara al catálogo, retirar una talla alteraría
    órdenes pasadas.

    No lleva `created_at`: la fecha de la línea es la de su orden.
    """

    __tablename__ = "order_item"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="cantidad_positiva"),
        CheckConstraint("unit_price_cop > 0", name="precio_positivo"),
        CheckConstraint(
            "line_total_cop = quantity * unit_price_cop", name="total_linea_coherente"
        ),
        # Una variante aparece una sola vez por orden: las cantidades se suman
        # antes de crear la orden, no después.
        UniqueConstraint(
            "order_id", "variant_id", name="uq_order_item_order_id_variant_id"
        ),
        Index("ix_order_item_order_id", "order_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=UUID_NUEVO
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_header.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # RESTRICT implementa RN-23: un producto vendido no puede desaparecer del
    # histórico.
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variant.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_name: Mapped[str] = mapped_column(String(120), nullable=False)
    size: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_cop: Mapped[int] = mapped_column(BigInteger, nullable=False)
    line_total_cop: Mapped[int] = mapped_column(BigInteger, nullable=False)


class Notification(Base):
    """Estado de los avisos de confirmación (REQ-05, riesgo R-08).

    Las notificaciones se crean y se despachan **fuera** de la transacción
    crítica: un fallo del servicio de correo no puede deshacer una orden ya
    confirmada (RN-14, RN-15).
    """

    __tablename__ = "notification"
    __table_args__ = (
        CheckConstraint(
            "recipient_type IN ('COMPRADOR', 'ADMINISTRADOR')", name="destinatario_valido"
        ),
        CheckConstraint(f"recipient ~* '{FORMA_CORREO}'", name="correo_formato"),
        CheckConstraint(
            "status IN ('PENDIENTE', 'ENVIADA', 'FALLIDA')", name="estado_valido"
        ),
        CheckConstraint("attempts >= 0", name="intentos_no_negativos"),
        Index("ix_notification_order_id", "order_id"),
        Index("ix_notification_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=UUID_NUEVO
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_header.id", ondelete="RESTRICT"),
        nullable=False,
    )
    recipient_type: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'PENDIENTE'")
    )
    attempts: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    last_error: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        MARCA_TIEMPO, nullable=False, server_default=text("now()")
    )
    sent_at: Mapped[datetime.datetime | None] = mapped_column(MARCA_TIEMPO, nullable=True)
