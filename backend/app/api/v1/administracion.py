"""Panel de administración: EP-13, EP-15, EP-17 a EP-21, EP-23 y EP-24.

Todas las rutas exigen `Administrador`, que resuelve el token y levanta
UNAUTHENTICATED si falta. La dependencia va en la firma de cada función y no en
un middleware por prefijo, para que no haya forma de añadir una ruta aquí y
olvidar protegerla.

Dos operaciones modifican inventario —el ajuste manual (EP-15) y la cancelación
de una orden (EP-18)— y las dos lo hacen bajo el mismo bloqueo de fila que la
compra. Un ajuste sin bloqueo podría pisar el descuento de una orden que esté
ocurriendo en ese instante.

Lo que no existe aquí es tan deliberado como lo que existe: no hay endpoint de
modificación ni de borrado de auditoría (RN-25), ni borrado físico de productos
u órdenes (RN-23, Ley 527 de 1999).
"""

from __future__ import annotations

import datetime
import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api import errores
from app.api.deps import Administrador, SesionDb
from app.api.v1.catalogo import _a_resumen, _consulta_resumen, aplicar_filtros, aplicar_orden
from app.api.v1.compra import _a_respuesta
from app.models.administracion import AuditLog
from app.models.catalogo import Inventory, Product, ProductVariant
from app.models.ordenes import Notification, OrderHeader, OrderItem
from app.schemas.catalogo import AdminProductSummaryResponse, InventoryResponse
from app.schemas.comunes import ModeloApi, Pagina
from app.schemas.ordenes import (
    InventoryAdjustmentRequest,
    OrderResponse,
    OrderStatusUpdateRequest,
    OrderSummaryResponse,
)

router = APIRouter(prefix="/admin", tags=["administración"])

# RN-13. Una orden entregada o cancelada es terminal: no se reabre.
TRANSICIONES: dict[str, list[str]] = {
    "CONFIRMADA": ["PREPARADA", "CANCELADA"],
    "PREPARADA": ["ENTREGADA", "CANCELADA"],
    "ENTREGADA": [],
    "CANCELADA": [],
}


class AuditEntryResponse(ModeloApi):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    action: str
    source: str
    old_value: str | None
    new_value: str
    reason: str | None
    created_at: datetime.datetime


class NotificationResponse(ModeloApi):
    id: uuid.UUID
    order_id: uuid.UUID
    recipient_type: str
    recipient: str
    status: str
    attempts: int
    created_at: datetime.datetime


# ------------------------------------------------------------- inventario


def _fila_inventario(v, inv, p, categoria, umbral) -> InventoryResponse:
    return InventoryResponse(
        variant_id=v.id,
        product_id=p.id,
        product_name=p.name,
        sku=v.sku,
        size=v.size,
        available_units=inv.stock_quantity,
        price_cop=p.price_cop,
        category_name=categoria,
        published=p.published,
        low_stock=inv.stock_quantity <= umbral,
    )


@router.get("/inventory", response_model=Pagina[InventoryResponse])
def ver_inventario(
    admin: Administrador,
    sesion: SesionDb,
    q: str | None = None,
    low_stock_threshold: Annotated[int, Query(ge=0, alias="lowStockThreshold")] = 3,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50, alias="pageSize")] = 20,
):
    """EP-24. Ordenado por existencias ascendentes: lo que está por agotarse
    aparece primero, que es la razón por la que alguien abre esta pantalla."""
    from app.models.catalogo import Category

    consulta = (
        select(ProductVariant, Inventory, Product, Category.name)
        .join(Inventory, Inventory.variant_id == ProductVariant.id)
        .join(Product, Product.id == ProductVariant.product_id)
        .join(Category, Category.id == Product.category_id)
        .where(ProductVariant.active.is_(True))
    )
    if q:
        consulta = consulta.where(
            func.unaccent(func.lower(Product.name)).contains(func.unaccent(func.lower(q)))
        )

    total = sesion.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    filas = sesion.execute(
        consulta.order_by(Inventory.stock_quantity.asc(), Product.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return Pagina.construir(
        [_fila_inventario(v, i, p, c, low_stock_threshold) for v, i, p, c in filas],
        pagina=page,
        tamano=page_size,
        total=total,
    )


@router.patch("/variants/{variant_id}/inventory", response_model=InventoryResponse)
def ajustar_inventario(
    variant_id: uuid.UUID,
    peticion: InventoryAdjustmentRequest,
    admin: Administrador,
    sesion: SesionDb,
):
    """EP-15. Fija el valor final y audita el cambio en la misma transacción.

    El bloqueo importa: sin él, un ajuste podría pisar el descuento de una
    compra que esté ocurriendo en ese mismo instante, y el valor guardado
    quedaría sin relación con lo realmente vendido.
    """
    from app.models.catalogo import Category

    inventario = sesion.scalar(
        select(Inventory).where(Inventory.variant_id == variant_id).with_for_update()
    )
    if inventario is None:
        raise errores.no_encontrado("La variante solicitada no existe")

    fila = sesion.execute(
        select(ProductVariant, Product, Category.name)
        .join(Product, Product.id == ProductVariant.product_id)
        .join(Category, Category.id == Product.category_id)
        .where(ProductVariant.id == variant_id)
    ).first()
    if fila is None:
        raise errores.no_encontrado("La variante solicitada no existe")
    variante, producto, categoria = fila

    anterior = inventario.stock_quantity
    inventario.stock_quantity = peticion.stock_quantity
    inventario.updated_at = datetime.datetime.now(datetime.timezone.utc)

    sesion.add(
        AuditLog(
            admin_user_id=admin.id,
            entity_type="INVENTORY",
            entity_id=variant_id,
            action="STOCK_CHANGE",
            source="AJUSTE_MANUAL",
            old_value=str(anterior),
            new_value=str(peticion.stock_quantity),
            reason=peticion.reason,
        )
    )
    sesion.commit()
    return _fila_inventario(variante, inventario, producto, categoria, 3)


# ----------------------------------------------------------------- órdenes


@router.get("/orders", response_model=Pagina[OrderSummaryResponse])
def listar_ordenes(
    admin: Administrador,
    sesion: SesionDb,
    status_filtro: Annotated[list[str] | None, Query(alias="status")] = None,
    q: str | None = None,
    date_from: Annotated[str | None, Query(alias="dateFrom")] = None,
    date_to: Annotated[str | None, Query(alias="dateTo")] = None,
    sort: str = "createdAt:desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50, alias="pageSize")] = 20,
):
    """EP-17. Listado de pedidos para preparar y despachar."""
    conteo = (
        select(OrderItem.order_id, func.count(OrderItem.id).label("n"))
        .group_by(OrderItem.order_id)
        .subquery()
    )
    consulta = select(OrderHeader, func.coalesce(conteo.c.n, 0)).outerjoin(
        conteo, conteo.c.order_id == OrderHeader.id
    )

    if status_filtro:
        if invalidos := [s for s in status_filtro if s not in TRANSICIONES]:
            raise errores.validacion(
                [{"field": "status", "issue": f"estado inexistente: {invalidos[0]}"}]
            )
        consulta = consulta.where(OrderHeader.status.in_(status_filtro))

    if q:
        patron = f"%{q.lower()}%"
        consulta = consulta.where(
            func.lower(OrderHeader.order_number).like(patron)
            | func.lower(OrderHeader.customer_name).like(patron)
        )

    def _fecha(valor: str, campo: str) -> datetime.date:
        try:
            return datetime.date.fromisoformat(valor)
        except ValueError:
            raise errores.validacion(
                [{"field": campo, "issue": "debe tener el formato AAAA-MM-DD"}]
            ) from None

    if date_from:
        # Desde el primer instante del día, en UTC: el contrato recibe una
        # fecha, pero la columna guarda marca de tiempo.
        consulta = consulta.where(
            OrderHeader.created_at
            >= datetime.datetime.combine(
                _fecha(date_from, "dateFrom"),
                datetime.time.min,
                tzinfo=datetime.timezone.utc,
            )
        )

    if date_to:
        # Hasta el último instante del día: con time.min, «hasta el 15» dejaría
        # fuera todas las órdenes del 15.
        consulta = consulta.where(
            OrderHeader.created_at
            <= datetime.datetime.combine(
                _fecha(date_to, "dateTo"),
                datetime.time.max,
                tzinfo=datetime.timezone.utc,
            )
        )

    campo, _, direccion = sort.partition(":")
    columnas = {"createdAt": OrderHeader.created_at, "totalCop": OrderHeader.total_cop}
    columna = columnas.get(campo)
    if columna is None:
        raise errores.validacion(
            [{"field": "sort", "issue": "valor de ordenamiento no admitido"}]
        )

    total = sesion.scalar(
        select(func.count()).select_from(consulta.order_by(None).subquery())
    ) or 0
    filas = sesion.execute(
        consulta.order_by(columna.desc() if direccion == "desc" else columna.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return Pagina.construir(
        [
            OrderSummaryResponse(
                id=o.id,
                order_number=o.order_number,
                status=o.status,
                total_cop=o.total_cop,
                created_at=o.created_at,
                customer_name=o.customer_name,
                item_count=int(n),
            )
            for o, n in filas
        ],
        pagina=page,
        tamano=page_size,
        total=total,
    )


@router.get("/orders/{order_id}", response_model=OrderResponse)
def detalle_orden(order_id: uuid.UUID, admin: Administrador, sesion: SesionDb):
    """EP-23. **Sin enmascarar**: el administrador necesita la dirección
    completa para despachar."""
    orden = sesion.get(OrderHeader, order_id)
    if orden is None:
        raise errores.no_encontrado("La orden solicitada no existe")
    lineas = sesion.scalars(select(OrderItem).where(OrderItem.order_id == orden.id)).all()
    return _a_respuesta(orden, lineas, enmascarar=False)


@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
def cambiar_estado(
    order_id: uuid.UUID,
    peticion: OrderStatusUpdateRequest,
    admin: Administrador,
    sesion: SesionDb,
):
    """EP-18. Cancelar devuelve las unidades al inventario en la misma
    transacción (RN-09): si la devolución fallara después de marcar la orden
    como cancelada, el inventario quedaría permanentemente por debajo de lo
    real y nadie lo notaría."""
    orden = sesion.get(OrderHeader, order_id)
    if orden is None:
        raise errores.no_encontrado("La orden solicitada no existe")

    permitidos = TRANSICIONES[orden.status]
    if peticion.status not in permitidos:
        raise errores.transicion_invalida(orden.status, peticion.status, permitidos)

    if peticion.status == "CANCELADA" and not peticion.reason:
        raise errores.validacion(
            [{"field": "reason", "issue": "obligatorio al cancelar una orden"}]
        )

    anterior = orden.status

    if peticion.status == "CANCELADA":
        lineas = sesion.scalars(
            select(OrderItem).where(OrderItem.order_id == orden.id)
        ).all()
        ids = sorted({l.variant_id for l in lineas})
        inventarios = {
            inv.variant_id: inv
            for inv in sesion.scalars(
                select(Inventory)
                .where(Inventory.variant_id.in_(ids))
                .order_by(Inventory.variant_id)
                .with_for_update()
            ).all()
        }
        for linea in lineas:
            inv = inventarios.get(linea.variant_id)
            if inv is None:
                continue
            previo = inv.stock_quantity
            inv.stock_quantity = previo + linea.quantity
            sesion.add(
                AuditLog(
                    admin_user_id=admin.id,
                    entity_type="INVENTORY",
                    entity_id=linea.variant_id,
                    action="STOCK_CHANGE",
                    source="CANCELACION",
                    old_value=str(previo),
                    new_value=str(previo + linea.quantity),
                    reason=peticion.reason,
                )
            )

    orden.status = peticion.status
    orden.updated_at = datetime.datetime.now(datetime.timezone.utc)
    sesion.add(
        AuditLog(
            admin_user_id=admin.id,
            entity_type="ORDER",
            entity_id=orden.id,
            action="STATUS_CHANGE",
            source="CANCELACION" if peticion.status == "CANCELADA" else "AJUSTE_MANUAL",
            old_value=anterior,
            new_value=peticion.status,
            reason=peticion.reason or f"Cambio de estado a {peticion.status}",
        )
    )
    sesion.commit()

    lineas = sesion.scalars(select(OrderItem).where(OrderItem.order_id == orden.id)).all()
    return _a_respuesta(orden, lineas, enmascarar=False)


# ---------------------------------------------------------------- catálogo


@router.get("/products", response_model=Pagina[AdminProductSummaryResponse])
def listar_productos_admin(
    admin: Administrador,
    sesion: SesionDb,
    q: str | None = None,
    category: Annotated[list[str] | None, Query()] = None,
    published: bool | None = None,
    sort: str = "createdAt:desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50, alias="pageSize")] = 20,
):
    """EP-21. Incluye despublicados, con `published` explícito."""
    consulta = aplicar_filtros(
        _consulta_resumen(publicados_solo=False),
        sesion,
        q=q,
        categorias=category,
        tallas=None,
        solo_con_stock=None,
    )
    if published is not None:
        consulta = consulta.where(Product.published.is_(published))

    total = sesion.scalar(
        select(func.count()).select_from(consulta.order_by(None).subquery())
    ) or 0
    filas = sesion.execute(
        aplicar_orden(consulta, sort).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return Pagina.construir(
        [_a_resumen(f, con_published=True) for f in filas],
        pagina=page,
        tamano=page_size,
        total=total,
    )


@router.patch("/products/{product_id}/publish", response_model=AdminProductSummaryResponse)
def publicar(
    product_id: uuid.UUID,
    cuerpo: dict,
    admin: Administrador,
    sesion: SesionDb,
):
    """EP-13. Despublicar **no borra** (RN-23): el producto sigue en la
    administración y en las órdenes previas."""
    producto = sesion.get(Product, product_id)
    if producto is None:
        raise errores.no_encontrado("El producto solicitado no existe")

    publicado = bool(cuerpo.get("published"))
    if publicado:
        # RN-21: publicar sin variantes activas dejaría en el catálogo un
        # producto que nadie puede comprar.
        activas = sesion.scalar(
            select(func.count())
            .select_from(ProductVariant)
            .where(
                ProductVariant.product_id == product_id,
                ProductVariant.active.is_(True),
            )
        )
        if not activas:
            raise errores.validacion(
                [{"field": "published", "issue": "el producto no tiene variantes activas"}]
            )

    anterior = producto.published
    producto.published = publicado
    sesion.add(
        AuditLog(
            admin_user_id=admin.id,
            entity_type="PRODUCT",
            entity_id=product_id,
            action="PUBLISH_CHANGE",
            source="AJUSTE_MANUAL",
            old_value=str(anterior).lower(),
            new_value=str(publicado).lower(),
            reason=cuerpo.get("reason") or "Cambio de publicación desde el panel",
        )
    )
    sesion.commit()

    fila = sesion.execute(
        _consulta_resumen(publicados_solo=False).where(Product.id == product_id)
    ).first()
    return _a_resumen(fila, con_published=True)


# ------------------------------------------------------ auditoría y avisos


@router.get("/audit-logs", response_model=Pagina[AuditEntryResponse])
def consultar_auditoria(
    admin: Administrador,
    sesion: SesionDb,
    entity_type: Annotated[str | None, Query(alias="entityType")] = None,
    entity_id: Annotated[uuid.UUID | None, Query(alias="entityId")] = None,
    action: str | None = None,
    source: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50, alias="pageSize")] = 20,
):
    """EP-19. Solo lectura: no existen endpoints de modificación ni de borrado
    de auditoría (RN-25), y el rol de la aplicación tampoco tiene el privilegio
    aunque alguien los escribiera."""
    consulta = select(AuditLog)
    for valor, columna in (
        (entity_type, AuditLog.entity_type),
        (entity_id, AuditLog.entity_id),
        (action, AuditLog.action),
        (source, AuditLog.source),
    ):
        if valor is not None:
            consulta = consulta.where(columna == valor)

    total = sesion.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    filas = sesion.scalars(
        consulta.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Pagina.construir(
        [AuditEntryResponse.model_validate(f) for f in filas],
        pagina=page,
        tamano=page_size,
        total=total,
    )


@router.get("/notifications", response_model=Pagina[NotificationResponse])
def consultar_notificaciones(
    admin: Administrador,
    sesion: SesionDb,
    status_filtro: Annotated[str | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50, alias="pageSize")] = 20,
):
    """EP-20. Mecanismo de degradación del riesgo R-08: si el correo falla, el
    administrador ve aquí qué pedidos no fueron notificados."""
    consulta = select(Notification)
    if status_filtro:
        consulta = consulta.where(Notification.status == status_filtro)

    total = sesion.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    filas = sesion.scalars(
        consulta.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Pagina.construir(
        [NotificationResponse.model_validate(f) for f in filas],
        pagina=page,
        tamano=page_size,
        total=total,
    )
