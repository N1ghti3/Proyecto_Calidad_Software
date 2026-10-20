"""Catálogo público: EP-01, EP-02 y EP-03.

Una decisión domina este módulo: **las existencias se agregan en la consulta,
no en Python**. Traer los productos y luego pedir el inventario de cada uno es
el patrón que hace lento un catálogo en cuanto crece —una consulta por
producto, y el número de consultas depende del tamaño de la página—. Con una
subconsulta agregada el costo es constante.

Sobre RN-01: un producto despublicado responde 404 y no 403. El catálogo
público no revela que exista; un 403 confirmaría que el identificador es
correcto, que es justo lo que no se quiere decir.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.api import errores
from app.api.deps import SesionDb
from app.models.catalogo import (
    Category,
    Inventory,
    Product,
    ProductImage,
    ProductVariant,
    SizeCatalog,
)
from app.schemas.catalogo import (
    AdminProductSummaryResponse,
    CategoryResponse,
    ProductImageResponse,
    ProductResponse,
    ProductSummaryResponse,
    ProductVariantResponse,
)
from app.schemas.comunes import Pagina
from app.servicios.ordenes import contar_publicados_por_categoria

router = APIRouter(tags=["catálogo"])

ORDENES_VALIDOS = {"name": Product.name, "priceCop": Product.price_cop, "createdAt": Product.created_at}


def _existencias_por_producto():
    """Subconsulta: unidades totales por producto, contando solo variantes activas."""
    return (
        select(
            ProductVariant.product_id.label("pid"),
            func.coalesce(func.sum(Inventory.stock_quantity), 0).label("unidades"),
            func.array_agg(ProductVariant.size).label("tallas"),
        )
        .join(Inventory, Inventory.variant_id == ProductVariant.id)
        .where(ProductVariant.active.is_(True))
        .group_by(ProductVariant.product_id)
        .subquery()
    )


def _imagen_principal():
    """Subconsulta: la imagen de menor `position` de cada producto.

    DISTINCT ON es específico de PostgreSQL y aquí está justificado: el motor
    está fijado por ADR-009, y la alternativa portable (función de ventana con
    filtro) es más larga y no más clara.
    """
    return (
        select(ProductImage.product_id, ProductImage.url, ProductImage.alt_text)
        .distinct(ProductImage.product_id)
        .order_by(ProductImage.product_id, ProductImage.position)
        .subquery()
    )


def _consulta_resumen(publicados_solo: bool) -> Select:
    stock, img = _existencias_por_producto(), _imagen_principal()
    consulta = (
        select(
            Product,
            Category.name.label("categoria"),
            func.coalesce(stock.c.unidades, 0).label("unidades"),
            stock.c.tallas,
            img.c.url,
            img.c.alt_text,
        )
        .join(Category, Category.id == Product.category_id)
        .outerjoin(stock, stock.c.pid == Product.id)
        .outerjoin(img, img.c.product_id == Product.id)
    )
    if publicados_solo:
        consulta = consulta.where(Product.published.is_(True))
    return consulta


def _a_resumen(fila, *, con_published: bool = False) -> ProductSummaryResponse:
    """Fila cruda de la consulta -> esquema de respuesta.

    `con_published` decide qué esquema sale: el de administración incluye el
    estado de publicación, el público no lo menciona.
    """
    p = fila[0]
    tallas = sorted({t for t in (fila.tallas or []) if t})
    unidades = int(fila.unidades or 0)
    datos = ProductSummaryResponse(
        id=p.id,
        slug=p.slug,
        name=p.name,
        price_cop=p.price_cop,
        category_name=fila.categoria,
        image_url=fila.url,
        image_alt=fila.alt_text,
        available_units=unidades,
        in_stock=unidades > 0,
        sizes=tallas,
    )
    if con_published:
        return AdminProductSummaryResponse(
            **datos.model_dump(by_alias=False), published=p.published
        )
    return datos


def aplicar_filtros(
    consulta: Select,
    sesion: Session,
    *,
    q: str | None,
    categorias: list[str] | None,
    tallas: list[str] | None,
    solo_con_stock: bool | None,
) -> Select:
    if q:
        # unaccent + lower: «camiseta» encuentra «Camisetá» y «CAMISETA». La
        # extensión la instala la migración inicial.
        consulta = consulta.where(
            func.unaccent(func.lower(Product.name)).contains(
                func.unaccent(func.lower(q))
            )
        )

    if categorias:
        existentes = set(
            sesion.scalars(select(Category.slug).where(Category.slug.in_(categorias))).all()
        )
        # Una categoría inexistente es un error de petición, no una página
        # vacía: la página vacía haría creer que la categoría existe pero no
        # tiene productos.
        if faltan := [c for c in categorias if c not in existentes]:
            raise errores.validacion(
                [{"field": "category", "issue": f"categoría inexistente: {faltan[0]}"}]
            )
        consulta = consulta.where(Category.slug.in_(categorias))

    if tallas:
        existentes = set(
            sesion.scalars(select(SizeCatalog.code).where(SizeCatalog.code.in_(tallas))).all()
        )
        if faltan := [t for t in tallas if t not in existentes]:
            raise errores.validacion(
                [{"field": "size", "issue": f"talla inexistente: {faltan[0]}"}]
            )
        consulta = consulta.where(
            Product.id.in_(
                select(ProductVariant.product_id).where(
                    ProductVariant.size.in_(tallas), ProductVariant.active.is_(True)
                )
            )
        )

    if solo_con_stock:
        consulta = consulta.where(
            Product.id.in_(
                select(ProductVariant.product_id)
                .join(Inventory, Inventory.variant_id == ProductVariant.id)
                .where(ProductVariant.active.is_(True), Inventory.stock_quantity > 0)
            )
        )
    return consulta


def aplicar_orden(consulta: Select, sort: str) -> Select:
    campo, _, direccion = sort.partition(":")
    columna = ORDENES_VALIDOS.get(campo)
    if columna is None or direccion not in ("", "asc", "desc"):
        raise errores.validacion(
            [{"field": "sort", "issue": "valor de ordenamiento no admitido"}]
        )
    return consulta.order_by(columna.desc() if direccion == "desc" else columna.asc())


@router.get("/products", response_model=Pagina[ProductSummaryResponse])
def listar_productos(
    sesion: SesionDb,
    q: Annotated[str | None, Query(min_length=2, max_length=80)] = None,
    category: Annotated[list[str] | None, Query()] = None,
    size: Annotated[list[str] | None, Query()] = None,
    in_stock: Annotated[bool | None, Query(alias="inStock")] = None,
    sort: str = "createdAt:desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50, alias="pageSize")] = 12,
):
    """EP-01. Catálogo paginado de productos publicados."""
    consulta = aplicar_filtros(
        _consulta_resumen(publicados_solo=True),
        sesion,
        q=q,
        categorias=category,
        tallas=size,
        solo_con_stock=in_stock,
    )
    total = sesion.scalar(
        select(func.count()).select_from(consulta.order_by(None).subquery())
    ) or 0
    filas = sesion.execute(
        aplicar_orden(consulta, sort).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return Pagina.construir(
        [_a_resumen(f) for f in filas], pagina=page, tamano=page_size, total=total
    )


@router.get("/categories", response_model=list[CategoryResponse])
def listar_categorias(sesion: SesionDb):
    """EP-02. Sin paginar: el catálogo de un micronegocio no lo justifica."""
    conteos = contar_publicados_por_categoria(sesion)
    categorias = sesion.scalars(select(Category).order_by(Category.name)).all()
    return [
        CategoryResponse(
            id=c.id, name=c.name, slug=c.slug, product_count=conteos.get(c.id, 0)
        )
        for c in categorias
    ]


@router.get("/products/{slug}", response_model=ProductResponse)
def detalle_producto(slug: str, sesion: SesionDb):
    """EP-03. Detalle con imágenes y disponibilidad por talla.

    Es el único endpoint que entrega los `variantId`, y por eso es
    **obligatorio para comprar**: el resumen trae los nombres de las tallas
    pero no sus identificadores (RN-05).
    """
    fila = sesion.execute(
        _consulta_resumen(publicados_solo=True).where(Product.slug == slug)
    ).first()
    if fila is None:
        raise errores.no_encontrado("El producto solicitado no existe")
    return construir_detalle(sesion, fila)


def detalle_por_id(sesion: Session, product_id) -> ProductResponse:
    """Detalle de cualquier producto, publicado o no. Solo para el panel."""
    fila = sesion.execute(
        _consulta_resumen(publicados_solo=False).where(Product.id == product_id)
    ).first()
    if fila is None:
        raise errores.no_encontrado("El producto solicitado no existe")
    return construir_detalle(sesion, fila)


def construir_detalle(sesion: Session, fila) -> ProductResponse:
    """Fila de `_consulta_resumen` -> ProductResponse con imágenes y tallas.

    Lo comparten el detalle público (EP-03) y el panel (EP-12, EP-22, EP-25),
    para que el producto recién creado o editado se vea exactamente como lo
    verá el comprador.
    """
    producto = fila[0]
    resumen = _a_resumen(fila)

    variantes = sesion.execute(
        select(ProductVariant, Inventory.stock_quantity)
        .join(Inventory, Inventory.variant_id == ProductVariant.id)
        .where(
            ProductVariant.product_id == producto.id,
            ProductVariant.active.is_(True),
        )
        .join(SizeCatalog, SizeCatalog.code == ProductVariant.size)
        # Por posición del catálogo de tallas (ADR-008) y no alfabético: S, M,
        # L, XL es el orden que un comprador espera; alfabéticamente sería
        # L, M, S, XL.
        .order_by(SizeCatalog.position)
    ).all()

    imagenes = sesion.scalars(
        select(ProductImage)
        .where(ProductImage.product_id == producto.id)
        .order_by(ProductImage.position)
    ).all()

    categoria = sesion.get(Category, producto.category_id)

    return ProductResponse(
        **resumen.model_dump(by_alias=False, exclude={"published"}),
        description=producto.description,
        category=CategoryResponse(
            id=categoria.id,
            name=categoria.name,
            slug=categoria.slug,
            product_count=0,
        ),
        images=[
            ProductImageResponse(
                id=i.id, url=i.url, alt=i.alt_text, position=i.position,
                width=i.width, height=i.height,
            )
            for i in imagenes
        ],
        published=producto.published,
        updated_at=producto.updated_at,
        variants=[
            ProductVariantResponse(
                id=v.id,
                sku=v.sku,
                size=v.size,
                available_units=stock,
                in_stock=stock > 0,
            )
            for v, stock in variantes
        ],
    )
