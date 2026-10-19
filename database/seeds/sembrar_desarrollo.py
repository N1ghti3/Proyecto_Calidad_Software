"""Siembra el catálogo de desarrollo y el usuario del panel.

Uso, desde la raíz del repositorio:

    backend\\.venv\\Scripts\\python.exe database\\seeds\\sembrar_desarrollo.py
    backend/.venv/bin/python   database/seeds/sembrar_desarrollo.py

Opciones:

    --reiniciar   Borra el catálogo existente antes de sembrar.
    --resumen     No siembra: solo informa qué hay en la base.

Decisiones que se ven en el código:

1. **Se conecta con `DATABASE_URL`**, es decir con el rol de la aplicación y no
   con el propietario. Así la siembra comprueba de paso que ese rol tiene los
   privilegios que necesita para trabajar de verdad. Si a alguien se le hubiera
   ido la mano con los `REVOKE`, esto falla aquí en lugar de fallar el día que la
   API intente crear un producto.
2. **Usa los modelos de SQLAlchemy**, no SQL escrito a mano. Un `INSERT` suelto
   puede quedar desalineado del esquema sin que nada avise; los modelos son los
   mismos de los que salió la migración.
3. **Se niega a sembrar sobre un catálogo que ya tiene datos**, salvo que se
   pida `--reiniciar`. Sembrar dos veces produciría un error de clave única a
   mitad de camino y dejaría la base a medio poblar.
4. **`--reiniciar` no toca `admin_user` ni `audit_log`.** La auditoría es de
   solo anexado (RN-25) y el rol de la aplicación no puede borrarla ni aunque
   quisiera; el usuario se actualiza en lugar de recrearse, porque la auditoría
   que firmó debe seguir apuntando a alguien.
5. **Todo en una transacción.** O queda el catálogo completo, o no queda nada.

La contraseña del administrador sale de `ADMIN_SEED_PASSWORD` y **nunca se
almacena**: lo que va a la base es su hash Argon2id (RN-20).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]

# Permite importar los modelos y la configuración del backend sin instalar el
# paquete ni depender de desde dónde se invoque el guion.
sys.path.insert(0, str(RAIZ_REPOSITORIO / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import create_engine, delete, func, select  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.seguridad import hashear_contrasena  # noqa: E402
from app.models import (  # noqa: E402
    AdminUser,
    Category,
    Inventory,
    Product,
    ProductImage,
    ProductVariant,
    SizeCatalog,
)
from catalogo_desarrollo import (  # noqa: E402
    ADMIN_CORREO,
    ADMIN_NOMBRE,
    CATEGORIAS,
    PRODUCTOS,
    SUFIJO_SKU_POR_TALLA,
)

RUTA_IMAGENES = "/media/productos/"

# La misma restricción que declara el esquema sobre product_variant.sku. Se
# repite aquí para poder fallar con un mensaje que diga qué SKU está mal, en
# lugar de dejar que el motor rechace la fila a mitad de la siembra.
FORMATO_SKU = re.compile(r"^[A-Z0-9-]+$")


def _construir_sku(base: str, talla: str) -> str:
    """Compone el SKU de una variante y comprueba su formato.

    El sufijo se traduce porque el SKU solo admite ASCII en mayúsculas: la talla
    «ÚNICA» lleva tilde y produciría un SKU inválido.
    """
    sufijo = SUFIJO_SKU_POR_TALLA.get(talla)
    if sufijo is None:
        raise SystemExit(
            f"No hay sufijo de SKU definido para la talla '{talla}'. "
            "Agrégalo a SUFIJO_SKU_POR_TALLA en catalogo_desarrollo.py."
        )

    sku = f"{base}-{sufijo}"
    if not FORMATO_SKU.match(sku):
        raise SystemExit(
            f"El SKU '{sku}' no cumple el formato exigido por el esquema "
            "([A-Z0-9-]+): solo letras mayúsculas sin tilde, dígitos y guiones."
        )
    return sku


# --------------------------------------------------------------------- entorno


def _url_de_la_aplicacion() -> str:
    """URL del rol de la aplicación, del entorno o del `.env` de la raíz."""
    url = os.getenv("DATABASE_URL")
    if not url:
        from app.core.config import obtener_settings

        url = obtener_settings().database_url
    return url


def _contrasena_del_administrador() -> str:
    url_env = os.getenv("ADMIN_SEED_PASSWORD")
    if url_env:
        return url_env

    # pydantic-settings ignora las claves que el modelo no declara, de modo que
    # este valor se lee directamente del archivo.
    archivo = RAIZ_REPOSITORIO / ".env"
    if archivo.is_file():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if linea.strip().startswith("ADMIN_SEED_PASSWORD="):
                valor = linea.split("=", 1)[1].strip().strip("'\"")
                if valor:
                    return valor

    raise SystemExit(
        "Falta ADMIN_SEED_PASSWORD. Es la contraseña del usuario administrador "
        "de desarrollo, mínimo 12 caracteres. Está declarada en .env.example: "
        "agrégala a tu .env de la raíz del repositorio."
    )


# ----------------------------------------------------------------- inspección


def _resumen(sesion: Session) -> dict[str, int]:
    return {
        "categorías": sesion.scalar(select(func.count()).select_from(Category)) or 0,
        "productos": sesion.scalar(select(func.count()).select_from(Product)) or 0,
        "publicados": sesion.scalar(
            select(func.count()).select_from(Product).where(Product.published.is_(True))
        )
        or 0,
        "variantes": sesion.scalar(select(func.count()).select_from(ProductVariant)) or 0,
        "imágenes": sesion.scalar(select(func.count()).select_from(ProductImage)) or 0,
        "tallas": sesion.scalar(select(func.count()).select_from(SizeCatalog)) or 0,
        "administradores": sesion.scalar(select(func.count()).select_from(AdminUser)) or 0,
    }


def _imprimir_resumen(titulo: str, datos: dict[str, int]) -> None:
    print(f"\n{titulo}")
    ancho = max(len(clave) for clave in datos)
    for clave, valor in datos.items():
        print(f"  {clave.rjust(ancho)}: {valor}")


# -------------------------------------------------------------------- siembra


def _borrar_catalogo(sesion: Session) -> None:
    """Borra el catálogo respetando el orden de las dependencias.

    No borra `size_catalog`: es parte del esquema y lo siembra la migración
    (ADR-008). Tampoco `admin_user` ni `audit_log`.

    Si alguna variante ya aparece en una orden, el borrado falla por la
    restricción de clave foránea. Eso **no es un defecto**: RN-23 impide que un
    producto vendido desaparezca del histórico. Para volver a empezar de cero
    con órdenes ya creadas, hay que recrear el volumen.
    """
    try:
        for tabla in (Inventory, ProductImage, ProductVariant, Product, Category):
            sesion.execute(delete(tabla))
    except IntegrityError as error:
        sesion.rollback()
        raise SystemExit(
            "No se puede borrar el catálogo: alguna variante ya aparece en una "
            "orden.\n\n"
            "Eso no es un defecto del guion, es RN-23 funcionando: un producto "
            "vendido no puede desaparecer del histórico, y la clave foránea lo "
            "impide en el motor.\n\n"
            "Para volver a empezar de cero, recrea el volumen — se pierden "
            "todos los datos:\n"
            "  docker compose down -v\n"
            "  docker compose up -d\n"
            "  cd backend && .venv/Scripts/python.exe -m alembic upgrade head\n\n"
            f"Detalle del motor: {error.orig}"
        ) from error

    print("  catálogo anterior borrado")


def _sembrar_catalogo(sesion: Session) -> None:
    categorias: dict[str, Category] = {}
    for nombre, slug in CATEGORIAS:
        categoria = Category(name=nombre, slug=slug)
        sesion.add(categoria)
        categorias[slug] = categoria
    sesion.flush()

    tallas_conocidas = set(sesion.scalars(select(SizeCatalog.code)).all())
    if not tallas_conocidas:
        raise SystemExit(
            "size_catalog está vacío. Esa semilla es parte del esquema y la "
            "crea la migración inicial: ejecuta 'alembic upgrade head' primero."
        )

    for datos in PRODUCTOS:
        producto = Product(
            category_id=categorias[datos["categoria"]].id,
            name=datos["name"],
            slug=datos["slug"],
            description=datos["description"],
            price_cop=datos["price_cop"],
            published=datos["published"],
        )
        sesion.add(producto)
        sesion.flush()

        for posicion, (archivo, alternativo, ancho, alto) in enumerate(
            datos["imagenes"]
        ):
            sesion.add(
                ProductImage(
                    product_id=producto.id,
                    url=f"{RUTA_IMAGENES}{archivo}",
                    alt_text=alternativo,
                    position=posicion,
                    width=ancho,
                    height=alto,
                )
            )

        for talla, unidades, activa in datos["variantes"]:
            if talla not in tallas_conocidas:
                raise SystemExit(
                    f"La talla '{talla}' de '{datos['name']}' no está en "
                    "size_catalog. Las tallas válidas son: "
                    + ", ".join(sorted(tallas_conocidas))
                )
            variante = ProductVariant(
                product_id=producto.id,
                sku=_construir_sku(datos["sku"], talla),
                size=talla,
                active=activa,
            )
            sesion.add(variante)
            sesion.flush()
            sesion.add(
                Inventory(variant_id=variante.id, stock_quantity=unidades)
            )

    sesion.flush()


def _sembrar_administrador(sesion: Session) -> None:
    """Crea el usuario del panel, o actualiza su contraseña si ya existe.

    No se recrea: `audit_log.admin_user_id` apunta a él con borrado restringido,
    y los registros que ya firmó deben seguir apuntando a alguien.
    """
    contrasena = _contrasena_del_administrador()
    hash_derivado = hashear_contrasena(contrasena)

    usuario = sesion.scalar(select(AdminUser).where(AdminUser.email == ADMIN_CORREO))
    if usuario is None:
        sesion.add(
            AdminUser(
                email=ADMIN_CORREO,
                password_hash=hash_derivado,
                full_name=ADMIN_NOMBRE,
            )
        )
        print(f"  administrador creado: {ADMIN_CORREO}")
    else:
        usuario.password_hash = hash_derivado
        usuario.active = True
        print(f"  administrador ya existía; contraseña actualizada: {ADMIN_CORREO}")


# ----------------------------------------------------------------------- main


def main() -> int:
    analizador = argparse.ArgumentParser(
        description="Siembra el catálogo de desarrollo de TiendaLocal."
    )
    analizador.add_argument(
        "--reiniciar",
        action="store_true",
        help="Borra el catálogo existente antes de sembrar.",
    )
    analizador.add_argument(
        "--resumen",
        action="store_true",
        help="Solo informa qué hay en la base; no siembra nada.",
    )
    argumentos = analizador.parse_args()

    motor = create_engine(_url_de_la_aplicacion(), echo=False)

    with Session(motor) as sesion:
        antes = _resumen(sesion)

        if argumentos.resumen:
            _imprimir_resumen("Estado de la base:", antes)
            return 0

        if antes["productos"] and not argumentos.reiniciar:
            _imprimir_resumen("La base ya tiene datos:", antes)
            print(
                "\nNo se sembró nada. Sembrar encima produciría un error de "
                "clave única a mitad de camino.\n"
                "Para reemplazar el catálogo:  --reiniciar"
            )
            return 1

        print("Sembrando…")
        if argumentos.reiniciar and antes["productos"]:
            _borrar_catalogo(sesion)

        _sembrar_catalogo(sesion)
        _sembrar_administrador(sesion)
        sesion.commit()

        _imprimir_resumen("Listo. Estado de la base:", _resumen(sesion))

    motor.dispose()
    print(
        "\nLas rutas de imagen apuntan a /media/productos/ y esos archivos "
        "todavía no existen:\nla interfaz mostrará el texto alternativo, que es "
        "una forma útil de revisarlo (RNF-03)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
