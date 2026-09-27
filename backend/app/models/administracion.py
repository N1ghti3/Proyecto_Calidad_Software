"""Modelos del panel administrativo y de la auditoría.

`audit_log` es la tabla que hace verificable el componente C6. La protección de
su inmutabilidad no está aquí: está en los privilegios del rol con el que se
conecta la aplicación, que la migración inicial revoca (ADR-010). Un modelo de
SQLAlchemy no puede impedir un UPDATE; un REVOKE sí.
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

MARCA_TIEMPO = DateTime(timezone=True)
UUID_NUEVO = text("gen_random_uuid()")

FORMA_CORREO = r"^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$"


class AdminUser(Base):
    """Operador autenticado del panel (REQ-06, RNF-04)."""

    __tablename__ = "admin_user"
    __table_args__ = (
        CheckConstraint(f"email ~ '{FORMA_CORREO}'", name="correo_formato"),
        # El correo se almacena en minúsculas, de modo que la unicidad sea real
        # y no dependa de cómo lo escribió quien creó el usuario.
        CheckConstraint("email = lower(email)", name="correo_minusculas"),
        CheckConstraint("length(trim(password_hash)) > 0", name="hash_no_vacio"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=UUID_NUEVO
    )
    email: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    # Resultado de una función de derivación de clave. **Nunca** la contraseña
    # en claro ni un resumen simple (RN-20).
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Permite revocar el acceso sin borrar el historial de auditoría que
    # este usuario firmó.
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    last_login_at: Mapped[datetime.datetime | None] = mapped_column(
        MARCA_TIEMPO, nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        MARCA_TIEMPO, nullable=False, server_default=text("now()")
    )


class AuditLog(Base):
    """Evidencia de variaciones de inventario y de estados de orden.

    Tabla de solo anexado (RN-25). Toda escritura en `inventory` genera un
    registro aquí dentro de la misma transacción (RN-24).
    """

    __tablename__ = "audit_log"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('INVENTORY', 'ORDER', 'PRODUCT')", name="entidad_valida"
        ),
        CheckConstraint(
            "action IN ('STOCK_CHANGE', 'STATUS_CHANGE', 'PUBLISH_CHANGE')",
            name="accion_valida",
        ),
        CheckConstraint(
            "source IN ('AJUSTE_MANUAL', 'ORDEN', 'CANCELACION')", name="origen_valido"
        ),
        CheckConstraint("length(trim(new_value)) > 0", name="valor_nuevo_no_vacio"),
        # El motivo es obligatorio salvo cuando el cambio lo originó una orden
        # del comprador, que no tiene a quién pedírselo. El ajuste manual
        # (EP-15) y la cancelación (EP-18) sí lo exigen (CA-06-0, CP-50).
        CheckConstraint(
            "source = 'ORDEN' OR reason IS NOT NULL", name="motivo_obligatorio"
        ),
        # Historial de una entidad concreta, de lo más reciente a lo más
        # antiguo: lo que muestra el panel.
        Index(
            "ix_audit_log_entity_type_entity_id_created_at",
            "entity_type",
            "entity_id",
            text("created_at DESC"),
        ),
        Index("ix_audit_log_created_at", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=UUID_NUEVO
    )
    # Nulo cuando el origen es una orden del comprador: no hay administrador
    # responsable de un descuento de inventario que hizo una compra.
    admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_user.id", ondelete="RESTRICT"),
        nullable=True,
    )
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # Sin clave foránea a propósito: la columna apunta a tablas distintas según
    # entity_type, y el registro debe sobrevivir a la entidad que describe.
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    old_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    new_value: Mapped[str] = mapped_column(String(120), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        MARCA_TIEMPO, nullable=False, server_default=text("now()")
    )
