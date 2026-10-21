"""Esquemas del carrito, el checkout y las órdenes.

El teléfono es el único campo con una transformación real: el contrato acepta
`+573001234567` del cliente, pero la base solo admite dígitos
(`ck_order_header_telefono_formato`). La normalización ocurre aquí, en el
borde, y no en la ruta ni en el servicio: así hay un solo lugar donde puede
fallar y un solo lugar que hay que leer para saber qué se guardó.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Annotated, Literal

from pydantic import Field, field_validator

from app.schemas.comunes import ModeloApi

ESTADOS = Literal["CONFIRMADA", "PREPARADA", "ENTREGADA", "CANCELADA"]

# RN-07: el tope por línea evita que una sola petición agote el inventario.
Cantidad = Annotated[int, Field(ge=1, le=20)]


class CartItemRequest(ModeloApi):
    variant_id: uuid.UUID
    quantity: Cantidad


class CartValidationRequest(ModeloApi):
    items: list[CartItemRequest] = Field(min_length=1, max_length=50)

    @field_validator("items")
    @classmethod
    def _sin_repetidos(cls, v: list[CartItemRequest]) -> list[CartItemRequest]:
        # Dos líneas con la misma variante harían ambiguo el descuento: ¿se
        # suman las cantidades o gana la última? El contrato prefiere rechazar.
        ids = [i.variant_id for i in v]
        if len(ids) != len(set(ids)):
            raise ValueError("no se admite la misma variante en dos líneas")
        return v


class CartLineResponse(ModeloApi):
    variant_id: uuid.UUID
    product_name: str
    size: str
    requested_quantity: int
    available_units: int
    available: bool
    unit_price_cop: int


class CartValidationResponse(ModeloApi):
    valid: bool
    items: list[CartLineResponse]
    # Total de las líneas satisfacibles (modelos.md). El frontend lo muestra
    # tal cual en lugar de sumar precios por su cuenta.
    total_cop: int
    checked_at: datetime.datetime


class CustomerRequest(ModeloApi):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=5, max_length=160)
    phone: str = Field(min_length=7, max_length=20)
    address: str = Field(min_length=5, max_length=200)
    city: str = Field(min_length=2, max_length=80)

    @field_validator("email")
    @classmethod
    def _correo(cls, v: str) -> str:
        v = v.strip().lower()
        # Comprobación mínima y deliberada: la validación fuerte vive en la
        # restricción de la base, que es la que no se puede evadir.
        if "@" not in v or "." not in v.split("@")[-1] or " " in v:
            raise ValueError("formato de correo inválido")
        return v

    @field_validator("phone")
    @classmethod
    def _telefono(cls, v: str) -> str:
        digitos = v.strip().removeprefix("+").replace(" ", "").replace("-", "")
        if not digitos.isdigit() or not 7 <= len(digitos) <= 15:
            raise ValueError("debe tener entre 7 y 15 dígitos")
        return digitos

    @field_validator("name", "address", "city")
    @classmethod
    def _sin_espacios_sobrantes(cls, v: str) -> str:
        limpio = v.strip()
        if not limpio:
            raise ValueError("no puede estar vacío")
        return limpio


class CustomerResponse(ModeloApi):
    """Datos del comprador tal como salen, sin validadores de entrada.

    Reutilizar `CustomerRequest` para responder hacía que la consulta pública
    (EP-06) fallara siempre con 500: el teléfono enmascarado `********4567`
    no pasa el validador que exige de 7 a 15 dígitos.
    """

    name: str
    email: str
    phone: str
    address: str
    city: str


class CreateOrderRequest(ModeloApi):
    items: list[CartItemRequest] = Field(min_length=1, max_length=50)
    customer: CustomerRequest
    data_processing_consent: bool
    privacy_notice_version: str = Field(default="1.0", max_length=20)

    @field_validator("items")
    @classmethod
    def _sin_repetidos(cls, v: list[CartItemRequest]) -> list[CartItemRequest]:
        ids = [i.variant_id for i in v]
        if len(ids) != len(set(ids)):
            raise ValueError("no se admite la misma variante en dos líneas")
        return v


class OrderItemResponse(ModeloApi):
    variant_id: uuid.UUID
    product_name: str
    size: str
    quantity: int
    unit_price_cop: int
    line_total_cop: int


class OrderResponse(ModeloApi):
    id: uuid.UUID
    order_number: str
    status: ESTADOS
    items: list[OrderItemResponse]
    total_cop: int
    customer: CustomerResponse
    # RN-12: el frontend muestra el aviso de que el pago es simulado.
    simulated_checkout: bool = True
    data_processing_consent: bool = True
    created_at: datetime.datetime


class OrderSummaryResponse(ModeloApi):
    id: uuid.UUID
    order_number: str
    status: ESTADOS
    total_cop: int
    created_at: datetime.datetime
    customer_name: str
    item_count: int


class OrderStatusUpdateRequest(ModeloApi):
    status: ESTADOS
    reason: str | None = Field(default=None, max_length=120)


class LoginRequest(ModeloApi):
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=1, max_length=200)


class AdminUserResponse(ModeloApi):
    id: uuid.UUID
    email: str
    full_name: str


class LoginResponse(ModeloApi):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: AdminUserResponse


class PublishRequest(ModeloApi):
    """EP-13. Antes era un `dict` sin validar: `{"published": "no"}` publicaba."""

    published: bool
    reason: str | None = Field(default=None, max_length=120)


class InventoryAdjustmentRequest(ModeloApi):
    """Fija el valor final, no un delta.

    Un delta obliga al panel a conocer el valor actual, y si otro ajuste ocurre
    entre la lectura y el envío, el resultado es incorrecto sin que nadie lo
    note. El valor absoluto no tiene esa ambigüedad.
    """

    stock_quantity: int = Field(ge=0)
    # RN-25: la auditoría sin motivo no sirve para auditar.
    reason: str = Field(min_length=3, max_length=120)
