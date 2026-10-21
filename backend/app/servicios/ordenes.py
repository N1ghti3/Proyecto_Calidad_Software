"""Creación de órdenes: la transacción que el proyecto existe para demostrar.

El problema real es una condición de carrera. Dos compradores piden la última
unidad en el mismo instante; ambos leen «queda 1», ambos concluyen que pueden
comprar, ambos descuentan. El resultado es una venta que no se puede despachar
y un contador de inventario que ya no describe la realidad.

La defensa de ADR-005 es bloqueo pesimista de fila:

    SELECT ... FROM inventory WHERE variant_id = ANY(...) ORDER BY variant_id
    FOR UPDATE

`FOR UPDATE` hace que la segunda transacción espere a que la primera termine,
de modo que lee el valor ya descontado y rechaza la compra. No es optimismo ni
reintento: es el motor serializando el acceso a esas filas concretas.

`ORDER BY variant_id` no es cosmético. Dos órdenes que tocan las mismas dos
variantes en orden distinto se bloquean mutuamente, cada una esperando la fila
que la otra tiene. Adquirir siempre en el mismo orden hace el interbloqueo
imposible por construcción, no improbable.

La verificación ocurre **después** del bloqueo y **antes** del descuento. Entre
esas dos líneas nadie más puede tocar esas filas, y ahí está toda la garantía.

Qué queda fuera de la transacción, y por qué: la notificación. Por RN-15 un
fallo de correo no invalida una compra. Si el envío viviera dentro, un servidor
de correo caído revertiría órdenes perfectamente válidas. Las notificaciones se
registran como PENDIENTE dentro de la transacción y se envían después del
COMMIT; si fallan, quedan visibles en el panel (EP-20).

Defensa en profundidad: aunque este código tuviera un defecto, la restricción
`ck_inventory_stock_no_negativo` impide que las existencias bajen de cero. La
aplicación es la primera línea; la base es la que no se puede evadir.
"""

from __future__ import annotations

import datetime
import secrets
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import errores
from app.models.administracion import AuditLog
from app.models.catalogo import Inventory, Product, ProductVariant
from app.models.ordenes import Notification, OrderHeader, OrderItem

# ADR-010: sin 0, 1, I ni O. Un número de orden se dicta por teléfono y se
# copia a mano; esos cuatro caracteres se confunden entre sí.
ALFABETO_ORDEN = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def nuevo_numero_orden() -> str:
    """Formato `TL-AAAAMMDD-XXXXX` (ADR-010)."""
    fecha = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    cola = "".join(secrets.choice(ALFABETO_ORDEN) for _ in range(5))
    return f"TL-{fecha}-{cola}"


def _lineas_solicitadas(items) -> dict[uuid.UUID, int]:
    return {i.variant_id: i.quantity for i in items}


def cargar_variantes(sesion: Session, ids: list[uuid.UUID]) -> dict[uuid.UUID, dict]:
    """Datos de cada variante activa de un producto publicado, sin bloquear.

    Sirve para la validación informativa del carrito (EP-04) y para componer
    los mensajes de error. La compra no se apoya en esta lectura.
    """
    filas = sesion.execute(
        select(
            ProductVariant.id,
            ProductVariant.size,
            Product.name,
            Product.price_cop,
            Inventory.stock_quantity,
        )
        .join(Product, Product.id == ProductVariant.product_id)
        .join(Inventory, Inventory.variant_id == ProductVariant.id)
        .where(
            ProductVariant.id.in_(ids),
            ProductVariant.active.is_(True),
            Product.published.is_(True),
        )
    ).all()
    return {
        f.id: {
            "size": f.size,
            "product_name": f.name,
            "price_cop": f.price_cop,
            "stock": f.stock_quantity,
        }
        for f in filas
    }


def validar_carrito(sesion: Session, items) -> tuple[bool, list[dict]]:
    """EP-04. Consulta informativa: **no reserva unidades** (RN-06).

    Devuelve 200 aunque alguna línea no esté disponible. El detalle viaja en
    `items[].available`, porque preguntar por la disponibilidad no es un error
    aunque la respuesta sea «no hay».
    """
    solicitadas = _lineas_solicitadas(items)
    datos = cargar_variantes(sesion, list(solicitadas))

    faltantes = [vid for vid in solicitadas if vid not in datos]
    if faltantes:
        raise errores.no_encontrado(
            "Alguna de las variantes solicitadas no existe o no está disponible"
        )

    lineas, todo_disponible = [], True
    for vid, cantidad in solicitadas.items():
        d = datos[vid]
        disponible = d["stock"] >= cantidad
        todo_disponible = todo_disponible and disponible
        lineas.append(
            {
                "variant_id": vid,
                "product_name": d["product_name"],
                "size": d["size"],
                "requested_quantity": cantidad,
                "available_units": d["stock"],
                "available": disponible,
                "unit_price_cop": d["price_cop"],
            }
        )
    return todo_disponible, lineas


def crear_orden(sesion: Session, peticion) -> OrderHeader:
    """EP-05. Verifica, descuenta y crea la orden en una sola transacción.

    Secuencia de validación del contrato, en este orden exacto, porque define
    qué error gana cuando varios aplican a la vez:

      1. Formato del cuerpo  → lo resuelve Pydantic antes de llegar aquí.
      2. Consentimiento      → CONSENT_REQUIRED (RN-16).
      3. Existencia          → NOT_FOUND.
      4. Existencias         → INSUFFICIENT_STOCK, ya dentro del bloqueo.

    Si devuelve, las unidades están descontadas y la orden es recuperable.
    Si levanta, no se descontó ninguna unidad.
    """
    # 2. Consentimiento. Antes de tocar la base: sin autorización no hay nada
    #    que consultar, y la Ley 1581 de 2012 no admite un «después lo pido».
    if not peticion.data_processing_consent:
        raise errores.consentimiento_requerido()

    solicitadas = _lineas_solicitadas(peticion.items)
    ids = sorted(solicitadas)

    # 3. Existencia y publicación, sin bloquear todavía. Una variante
    #    inexistente es un 404 y no merece bloquear filas de nadie.
    datos = cargar_variantes(sesion, ids)
    if len(datos) != len(ids):
        raise errores.no_encontrado(
            "Alguna de las variantes solicitadas no existe o no está disponible"
        )

    # ---------------------------------------------------------- transacción
    # 4. Bloqueo. Desde aquí hasta el COMMIT, estas filas son nuestras.
    #    `with_for_update()` emite FOR UPDATE; el ORDER BY previene interbloqueos.
    bloqueadas = sesion.execute(
        select(Inventory)
        .where(Inventory.variant_id.in_(ids))
        .order_by(Inventory.variant_id)
        .with_for_update()
    ).scalars().all()

    inventario = {inv.variant_id: inv for inv in bloqueadas}

    # Verificación contra el valor recién bloqueado, no contra la lectura
    # anterior: esa pudo quedar obsoleta mientras esperábamos el bloqueo, y
    # justamente ese desfase es el defecto que el proyecto previene.
    insuficientes = [
        {
            "variantId": str(vid),
            "productName": datos[vid]["product_name"],
            "size": datos[vid]["size"],
            "requestedQuantity": cantidad,
            "availableUnits": inventario[vid].stock_quantity,
        }
        for vid, cantidad in solicitadas.items()
        if inventario[vid].stock_quantity < cantidad
    ]
    if insuficientes:
        # Sin descontar nada. El rollback lo hace la ruta al propagarse el error.
        raise errores.existencias_insuficientes(insuficientes)

    total = sum(datos[vid]["price_cop"] * c for vid, c in solicitadas.items())

    orden = OrderHeader(
        order_number=nuevo_numero_orden(),
        status="CONFIRMADA",
        total_cop=total,
        customer_name=peticion.customer.name,
        customer_email=peticion.customer.email,
        customer_phone=peticion.customer.phone,
        shipping_address=peticion.customer.address,
        shipping_city=peticion.customer.city,
        data_processing_consent=True,
        privacy_notice_version=peticion.privacy_notice_version,
    )
    sesion.add(orden)
    sesion.flush()  # necesitamos orden.id para las líneas

    for vid, cantidad in solicitadas.items():
        d = datos[vid]
        anterior = inventario[vid].stock_quantity
        inventario[vid].stock_quantity = anterior - cantidad

        sesion.add(
            OrderItem(
                order_id=orden.id,
                variant_id=vid,
                # Nombre, talla y precio se copian, no se referencian: una orden
                # debe seguir diciendo qué se vendió y a qué precio aunque el
                # producto cambie después (RN-28).
                product_name=d["product_name"],
                size=d["size"],
                quantity=cantidad,
                unit_price_cop=d["price_cop"],
                line_total_cop=d["price_cop"] * cantidad,
            )
        )
        sesion.add(
            AuditLog(
                # Nulo a propósito: ningún administrador es responsable de un
                # descuento que hizo una compra del público.
                admin_user_id=None,
                entity_type="INVENTORY",
                entity_id=vid,
                action="STOCK_CHANGE",
                source="ORDEN",
                old_value=str(anterior),
                new_value=str(anterior - cantidad),
                # La referencia a la orden (PRB-07, REQ-06): sin ella, con varias
                # compras simultáneas no se puede conciliar qué pedido descontó
                # qué unidades. ck_audit_log_motivo_obligatorio no la exige para
                # source = ORDEN, pero nada impide guardarla.
                reason=f"Orden {orden.order_number}",
            )
        )

    # Notificaciones PENDIENTE dentro de la transacción; el envío va después
    # del COMMIT y su fallo no cambia la respuesta (RN-15).
    sesion.add(
        Notification(
            order_id=orden.id,
            recipient_type="COMPRADOR",
            recipient=peticion.customer.email,
            status="PENDIENTE",
        )
    )
    return orden


def inventario_actual(sesion: Session, variant_id: uuid.UUID) -> int:
    fila = sesion.get(Inventory, variant_id)
    return fila.stock_quantity if fila else 0


def contar_publicados_por_categoria(sesion: Session) -> dict[uuid.UUID, int]:
    """Conteos para el filtro del catálogo.

    Una sola consulta agrupada en lugar de una por categoría: con pocas
    categorías la diferencia es invisible, pero la consulta por categoría es el
    patrón que hace lento un catálogo cuando crece.
    """
    filas = sesion.execute(
        select(Product.category_id, func.count(Product.id))
        .where(Product.published.is_(True))
        .group_by(Product.category_id)
    ).all()
    return {cid: n for cid, n in filas}
