"""Alta y edición de productos: EP-12, EP-14, EP-16, EP-22 y EP-25.

Como en `administracion.py`, cada ruta exige `Administrador` en su firma.

EP-25 (`GET /admin/products/{id}`) no estaba en el contrato original y se
agregó con esta pantalla: el detalle público (EP-03) responde 404 para los
productos despublicados (RN-01), y el formulario de edición necesita leerlos.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api import errores
from app.api.deps import Administrador, SesionDb
from app.api.v1.catalogo import detalle_por_id
from app.core.config import obtener_settings
from app.models.catalogo import Inventory, Product, ProductImage
from app.schemas.catalogo import (
    ProductCreateRequest,
    ProductImageResponse,
    ProductResponse,
    ProductUpdateRequest,
    ProductVariantResponse,
    VariantRequest,
)
from app.servicios import productos as servicio
from app.servicios.imagenes import FORMATOS, ImagenNoAdmitida, optimizar_y_guardar

router = APIRouter(prefix="/admin", tags=["administración"])


def _producto(sesion: SesionDb, product_id: uuid.UUID) -> Product:
    producto = sesion.get(Product, product_id)
    if producto is None:
        raise errores.no_encontrado("El producto solicitado no existe")
    return producto


def _confirmar(sesion: SesionDb) -> None:
    """Las comprobaciones previas cubren los casos esperados; esto atrapa la
    carrera en la que dos administradores crean el mismo SKU a la vez."""
    try:
        sesion.commit()
    except IntegrityError:
        sesion.rollback()
        raise errores.conflicto("sku", "otro registro tomó ese valor al mismo tiempo") from None


@router.get("/products/{product_id}", response_model=ProductResponse)
def detalle_admin(product_id: uuid.UUID, admin: Administrador, sesion: SesionDb):
    """EP-25. Detalle de cualquier producto, publicado o no."""
    return detalle_por_id(sesion, product_id)


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def crear(peticion: ProductCreateRequest, admin: Administrador, sesion: SesionDb):
    """EP-12. Nace despublicado salvo que se envíe `published: true`."""
    producto = servicio.crear_producto(sesion, peticion, admin)
    _confirmar(sesion)
    return detalle_por_id(sesion, producto.id)


@router.patch("/products/{product_id}", response_model=ProductResponse)
def editar(product_id: uuid.UUID, peticion: ProductUpdateRequest, admin: Administrador, sesion: SesionDb):
    """EP-22. Solo se aplican los campos enviados."""
    servicio.editar_producto(sesion, _producto(sesion, product_id), peticion, admin)
    _confirmar(sesion)
    return detalle_por_id(sesion, product_id)


@router.post(
    "/products/{product_id}/variants",
    response_model=ProductVariantResponse,
    status_code=status.HTTP_201_CREATED,
)
def agregar_variante(product_id: uuid.UUID, peticion: VariantRequest, admin: Administrador, sesion: SesionDb):
    """EP-14. Talla nueva con sus existencias iniciales, auditadas (RN-24)."""
    producto = _producto(sesion, product_id)
    variante = servicio.agregar_variante(sesion, producto, peticion, servicio.base_sku_de(sesion, producto), admin)
    _confirmar(sesion)
    stock = sesion.scalar(select(Inventory.stock_quantity).where(Inventory.variant_id == variante.id)) or 0
    return ProductVariantResponse(
        id=variante.id, sku=variante.sku, size=variante.size, available_units=stock, in_stock=stock > 0
    )


@router.post(
    "/products/{product_id}/images",
    response_model=ProductImageResponse,
    status_code=status.HTTP_201_CREATED,
)
def cargar_imagen(
    product_id: uuid.UUID,
    admin: Administrador,
    sesion: SesionDb,
    file: Annotated[UploadFile, File(description="JPEG, PNG o WebP")],
    alt: Annotated[str, Form(min_length=1, max_length=160)],
    position: Annotated[int | None, Form(ge=0, le=99)] = None,
):
    """EP-16. Se guarda una versión optimizada en WebP (RN-22).

    `alt` es obligatorio porque RNF-03 exige texto alternativo: una foto sin
    descripción es invisible para un lector de pantalla.
    """
    producto = _producto(sesion, product_id)
    alt = alt.strip()
    if not alt:
        raise errores.validacion([{"field": "alt", "issue": "no puede estar vacío"}])

    ajustes = obtener_settings()
    # Se lee un byte de más para saber si el archivo se pasó del límite sin
    # cargarlo entero en memoria.
    contenido = file.file.read(ajustes.imagen_max_bytes + 1)
    if len(contenido) > ajustes.imagen_max_bytes:
        raise errores.archivo_muy_grande(ajustes.imagen_max_bytes)

    if position is None:
        ultima = sesion.scalar(
            select(func.max(ProductImage.position)).where(ProductImage.product_id == producto.id)
        )
        position = 0 if ultima is None else ultima + 1
    elif sesion.scalar(
        select(func.count()).select_from(ProductImage).where(
            ProductImage.product_id == producto.id, ProductImage.position == position
        )
    ):
        raise errores.conflicto("position", str(position))

    try:
        guardada = optimizar_y_guardar(contenido, ajustes.carpeta_media, producto.id, ajustes.imagen_ancho_max)
    except ImagenNoAdmitida:
        raise errores.tipo_no_admitido(sorted(FORMATOS.values())) from None

    imagen = ProductImage(
        product_id=producto.id,
        url=f"/media/{guardada.ruta_relativa}",
        alt_text=alt,
        position=position,
        width=guardada.ancho,
        height=guardada.alto,
    )
    sesion.add(imagen)
    try:
        sesion.commit()
    except IntegrityError:
        # Otra carga tomó la misma posición en el mismo instante: el archivo
        # recién escrito quedaría huérfano, así que se borra.
        sesion.rollback()
        (ajustes.carpeta_media / guardada.ruta_relativa).unlink(missing_ok=True)
        raise errores.conflicto("position", str(position)) from None

    return ProductImageResponse(
        id=imagen.id, url=imagen.url, alt=imagen.alt_text, position=imagen.position,
        width=imagen.width, height=imagen.height,
    )
