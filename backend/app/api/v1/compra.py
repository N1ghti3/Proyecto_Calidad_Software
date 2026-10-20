"""Carrito, checkout y consulta de orden: EP-04, EP-05 y EP-06.

La frontera de la transacción vive aquí, no en el servicio: el servicio prepara
y modifica, la ruta decide cuándo confirmar. Si el servicio levanta cualquier
error, el `commit` nunca se ejecuta y la sesión se cierra con reversión
implícita, de modo que la garantía «409 ⇒ no se descontó nada» no depende de
recordar un rollback en cada rama de error.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, status
from sqlalchemy import select

from app.api import errores
from app.api.deps import SesionDb
from app.models.ordenes import Notification, OrderHeader, OrderItem
from app.schemas.ordenes import (
    CartValidationRequest,
    CartValidationResponse,
    CreateOrderRequest,
    CustomerRequest,
    OrderItemResponse,
    OrderResponse,
)
from app.servicios import ordenes as servicio

router = APIRouter(tags=["compra"])
registro = logging.getLogger("tiendalocal.api")


def _a_respuesta(orden: OrderHeader, lineas: list[OrderItem], *, enmascarar: bool) -> OrderResponse:
    return OrderResponse(
        id=orden.id,
        order_number=orden.order_number,
        status=orden.status,
        total_cop=orden.total_cop,
        created_at=orden.created_at,
        data_processing_consent=orden.data_processing_consent,
        items=[
            OrderItemResponse(
                variant_id=l.variant_id,
                product_name=l.product_name,
                size=l.size,
                quantity=l.quantity,
                unit_price_cop=l.unit_price_cop,
                subtotal_cop=l.line_total_cop,
            )
            for l in lineas
        ],
        customer=CustomerRequest(
            name=orden.customer_name,
            email=_enmascarar_correo(orden.customer_email) if enmascarar else orden.customer_email,
            phone=_enmascarar_telefono(orden.customer_phone) if enmascarar else orden.customer_phone,
            address=orden.shipping_address,
            city=orden.shipping_city,
        ),
    )


def _enmascarar_correo(correo: str) -> str:
    """RN-18. Reduce el daño si alguien obtiene un número de orden ajeno:
    basta para reconocer la propia orden, no para saber de quién es."""
    usuario, _, dominio = correo.partition("@")
    return f"{usuario[:1]}***@{dominio}"


def _enmascarar_telefono(telefono: str) -> str:
    return f"{'*' * max(0, len(telefono) - 4)}{telefono[-4:]}"


@router.post("/cart/validate", response_model=CartValidationResponse)
def validar_carrito(peticion: CartValidationRequest, sesion: SesionDb):
    """EP-04. Comprueba disponibilidad. **No reserva unidades** (RN-06).

    Devuelve 200 aunque alguna línea no alcance: preguntar por la
    disponibilidad no es un error aunque la respuesta sea «no hay». El detalle
    viaja en `items[].available`.
    """
    valido, lineas = servicio.validar_carrito(sesion, peticion.items)
    return CartValidationResponse(valid=valido, items=lineas)


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def crear_orden(peticion: CreateOrderRequest, sesion: SesionDb):
    """EP-05. El endpoint crítico del proyecto.

    Si responde 201, las unidades ya están descontadas y la orden es
    recuperable por EP-06. Si responde 409, no se descontó ninguna unidad.
    """
    orden = servicio.crear_orden(sesion, peticion)
    sesion.commit()

    lineas = sesion.scalars(
        select(OrderItem).where(OrderItem.order_id == orden.id)
    ).all()

    # Después del COMMIT, y fuera de él: por RN-15 un fallo de correo no
    # invalida una compra ya confirmada. Aquí no hay servidor de correo (DT-01),
    # así que la notificación queda PENDIENTE y visible en el panel (EP-20).
    try:
        _despachar_notificaciones(sesion, orden)
    except Exception:  # noqa: BLE001 — nada de esto puede tumbar la respuesta
        registro.exception("Fallo al despachar notificaciones de %s", orden.order_number)

    return _a_respuesta(orden, lineas, enmascarar=False)


def _despachar_notificaciones(sesion: SesionDb, orden: OrderHeader) -> None:
    """Marcador del envío real.

    Mientras REQ-05 siga diferido (DT-01), las notificaciones se quedan en
    PENDIENTE. Se deja la función aislada para que integrar un servicio de
    correo sea cambiar solo este cuerpo.
    """
    pendientes = sesion.scalars(
        select(Notification).where(
            Notification.order_id == orden.id, Notification.status == "PENDIENTE"
        )
    ).all()
    registro.info(
        "Orden %s confirmada; %d notificación(es) pendiente(s) de envío",
        orden.order_number,
        len(pendientes),
    )


@router.get("/orders/{order_number}", response_model=OrderResponse)
def consultar_orden(
    order_number: str,
    sesion: SesionDb,
    email: str = Query(..., description="Correo con que se creó la orden"),
):
    """EP-06. Consulta de la propia orden (RN-18).

    Exige número **y** correo. Si el par no coincide responde 404 y no 403:
    un 403 confirmaría que el número existe, que es exactamente lo que no se
    quiere revelar a quien prueba números al azar.
    """
    orden = sesion.scalar(
        select(OrderHeader).where(
            OrderHeader.order_number == order_number,
            OrderHeader.customer_email == email.strip().lower(),
        )
    )
    if orden is None:
        raise errores.no_encontrado("No existe una orden con ese número y correo")

    lineas = sesion.scalars(
        select(OrderItem).where(OrderItem.order_id == orden.id)
    ).all()
    return _a_respuesta(orden, lineas, enmascarar=True)
