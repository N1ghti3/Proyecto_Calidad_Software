"""Alta y edición de productos desde el panel (EP-12, EP-14, EP-22).

Las rutas solo traducen HTTP; aquí viven las reglas:

- **El slug se genera y no cambia.** Sale del nombre al crear el producto y
  se conserva aunque el nombre se edite después: el slug es la dirección
  pública (`/producto/<slug>`), y cambiarla rompería los enlaces que ya se
  compartieron.
- **El SKU se genera si no viene**, con la convención de la siembra:
  `TL-<CAT>-<NNN>-<TALLA>`. El prefijo de categoría se toma de los productos
  que ya existen en ella, para no inventar uno distinto del que el negocio usa.
- **Toda existencia inicial se audita** (RN-24), igual que un ajuste manual:
  un inventario que aparece sin registro no se puede conciliar.
"""

from __future__ import annotations

import datetime
import re
import unicodedata

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api import errores
from app.models.administracion import AdminUser, AuditLog
from app.models.catalogo import Category, Inventory, Product, ProductVariant, SizeCatalog
from app.schemas.catalogo import ProductCreateRequest, ProductUpdateRequest, VariantRequest


def _ascii(texto: str) -> str:
    """«Ñandú» -> «Nandu». Para slugs y SKU, que solo admiten ASCII."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def slug_unico(sesion: Session, nombre: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", _ascii(nombre).lower()).strip("-")[:120] or "producto"
    slug, n = base, 2
    while sesion.scalar(select(func.count()).select_from(Product).where(Product.slug == slug)):
        slug, n = f"{base}-{n}", n + 1
    return slug


def _sufijo_talla(talla: str) -> str:
    """Igual que SUFIJO_SKU_POR_TALLA de la siembra: «ÚNICA» -> «UNI»."""
    limpio = re.sub(r"[^A-Z0-9]", "", _ascii(talla).upper())
    return limpio if len(limpio) <= 3 else limpio[:3]


def base_sku_nueva(sesion: Session, categoria: Category) -> str:
    """`TL-CAM-005`: prefijo de la categoría y el siguiente número libre."""
    existente = sesion.scalar(
        select(ProductVariant.sku)
        .join(Product, Product.id == ProductVariant.product_id)
        .where(Product.category_id == categoria.id)
        .limit(1)
    )
    m = re.match(r"^([A-Z0-9]+-[A-Z0-9]+)-\d+", existente or "")
    prefijo = m.group(1) if m else f"TL-{re.sub(r'[^A-Z0-9]', '', _ascii(categoria.slug).upper())[:3] or 'GEN'}"

    numeros = [
        int(x.group(1))
        for sku in sesion.scalars(select(ProductVariant.sku).where(ProductVariant.sku.like(f"{prefijo}-%")))
        if (x := re.match(rf"^{re.escape(prefijo)}-(\d+)", sku))
    ]
    return f"{prefijo}-{max(numeros, default=0) + 1:03d}"


def base_sku_de(sesion: Session, producto: Product) -> str:
    """Base de los SKU que ya tiene el producto, para que una talla nueva
    (EP-14) quede con el mismo código que sus hermanas."""
    sku = sesion.scalar(select(ProductVariant.sku).where(ProductVariant.product_id == producto.id).limit(1))
    if sku and (m := re.match(r"^(.+)-[A-Z0-9]+$", sku)):
        return m.group(1)
    return base_sku_nueva(sesion, sesion.get(Category, producto.category_id))


def _tallas_validas(sesion: Session) -> list[str]:
    return list(sesion.scalars(
        select(SizeCatalog.code).where(SizeCatalog.active.is_(True)).order_by(SizeCatalog.position)
    ))


def agregar_variante(
    sesion: Session, producto: Product, peticion: VariantRequest, base_sku: str,
    admin: AdminUser, campo: str = "size",
) -> ProductVariant:
    tallas = _tallas_validas(sesion)
    if peticion.size not in tallas:
        raise errores.validacion(
            [{"field": campo, "issue": f"talla inexistente: {peticion.size}. Válidas: {', '.join(tallas)}"}]
        )
    repetida = sesion.scalar(
        select(func.count()).select_from(ProductVariant).where(
            ProductVariant.product_id == producto.id, ProductVariant.size == peticion.size
        )
    )
    if repetida:
        raise errores.conflicto("size", peticion.size)

    sku = peticion.sku or f"{base_sku}-{_sufijo_talla(peticion.size)}"
    if sesion.scalar(select(func.count()).select_from(ProductVariant).where(ProductVariant.sku == sku)):
        raise errores.conflicto("sku", sku)

    variante = ProductVariant(product_id=producto.id, sku=sku, size=peticion.size, active=peticion.active)
    sesion.add(variante)
    sesion.flush()  # obtiene el id que genera la base
    sesion.add(Inventory(variant_id=variante.id, stock_quantity=peticion.initial_stock))
    sesion.add(AuditLog(
        admin_user_id=admin.id,
        entity_type="INVENTORY",
        entity_id=variante.id,
        action="STOCK_CHANGE",
        source="AJUSTE_MANUAL",
        old_value=None,
        new_value=str(peticion.initial_stock),
        reason="Existencias iniciales de la talla",
    ))
    producto.updated_at = datetime.datetime.now(datetime.timezone.utc)
    return variante


def _categoria(sesion: Session, category_id) -> Category:
    categoria = sesion.get(Category, category_id)
    if categoria is None:
        raise errores.validacion([{"field": "categoryId", "issue": "la categoría no existe"}])
    return categoria


def _auditar_publicacion(sesion: Session, producto: Product, anterior: bool, admin: AdminUser) -> None:
    sesion.add(AuditLog(
        admin_user_id=admin.id,
        entity_type="PRODUCT",
        entity_id=producto.id,
        action="PUBLISH_CHANGE",
        source="AJUSTE_MANUAL",
        old_value=str(anterior).lower(),
        new_value=str(producto.published).lower(),
        reason="Cambio de publicación desde la edición del producto",
    ))


def crear_producto(sesion: Session, peticion: ProductCreateRequest, admin: AdminUser) -> Product:
    """EP-12. Producto, tallas y existencias iniciales en una sola transacción:
    si una talla falla, no queda un producto a medias."""
    categoria = _categoria(sesion, peticion.category_id)

    tallas = [v.size for v in peticion.variants]
    if repetidas := sorted({t for t in tallas if tallas.count(t) > 1}):
        raise errores.conflicto("size", repetidas[0])
    # RN-21: publicar exige al menos una talla activa.
    if peticion.published and not any(v.active for v in peticion.variants):
        raise errores.validacion([{"field": "published", "issue": "el producto no tiene variantes activas"}])

    producto = Product(
        category_id=categoria.id,
        name=peticion.name,
        slug=slug_unico(sesion, peticion.name),
        description=peticion.description,
        price_cop=peticion.price_cop,
        published=peticion.published,
    )
    sesion.add(producto)
    sesion.flush()

    base = base_sku_nueva(sesion, categoria)
    for i, v in enumerate(peticion.variants):
        agregar_variante(sesion, producto, v, base, admin, campo=f"variants.{i}.size")
    if peticion.published:
        _auditar_publicacion(sesion, producto, False, admin)
    return producto


def editar_producto(
    sesion: Session, producto: Product, peticion: ProductUpdateRequest, admin: AdminUser
) -> Product:
    """EP-22. Solo cambia lo enviado. Cambiar el precio no altera órdenes
    previas: cada línea guarda el precio vigente al comprar (RN-28)."""
    enviados = peticion.model_fields_set
    nulos = [c for c in ("name", "price_cop", "category_id", "published")
             if c in enviados and getattr(peticion, c) is None]
    if nulos:
        alias = {"name": "name", "price_cop": "priceCop", "category_id": "categoryId", "published": "published"}
        raise errores.validacion([{"field": alias[c], "issue": "no puede ser null"} for c in nulos])

    if "name" in enviados:
        producto.name = peticion.name  # el slug no cambia: ver el encabezado
    if "description" in enviados:
        producto.description = peticion.description
    if "price_cop" in enviados:
        producto.price_cop = peticion.price_cop
    if "category_id" in enviados:
        producto.category_id = _categoria(sesion, peticion.category_id).id
    if "published" in enviados and peticion.published != producto.published:
        if peticion.published:
            activas = sesion.scalar(
                select(func.count()).select_from(ProductVariant).where(
                    ProductVariant.product_id == producto.id, ProductVariant.active.is_(True)
                )
            )
            if not activas:
                raise errores.validacion([{"field": "published", "issue": "el producto no tiene variantes activas"}])
        anterior = producto.published
        producto.published = peticion.published
        _auditar_publicacion(sesion, producto, anterior, admin)

    producto.updated_at = datetime.datetime.now(datetime.timezone.utc)
    return producto
