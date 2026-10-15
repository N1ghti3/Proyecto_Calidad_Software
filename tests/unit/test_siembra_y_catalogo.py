"""Coherencia de los datos de siembra con el esquema, sin base de datos.

Detecta antes de tocar el motor un catálogo de desarrollo que la base rechazaría
a mitad de la siembra: SKU inválidos, tallas fuera del catálogo o productos que
no cumplen las precondiciones de las auditorías (CP-80, CP-81).
"""

from __future__ import annotations

import importlib.util
import re

import pytest

from apoyo import BACKEND
from catalogo_desarrollo import CATEGORIAS, PRODUCTOS, SUFIJO_SKU_POR_TALLA
from sembrar_desarrollo import _construir_sku

# Las mismas expresiones que declara el esquema.
FORMATO_SKU = re.compile(r"^[A-Z0-9-]+$")
FORMATO_SLUG = re.compile(r"^[a-z0-9-]+$")


def _tallas_de_la_migracion() -> set[str]:
    """Lee TALLAS_INICIALES de la migración, que es quien siembra size_catalog."""
    (ruta,) = (BACKEND / "alembic" / "versions").glob("*_esquema_inicial.py")
    spec = importlib.util.spec_from_file_location("migracion_inicial", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return {codigo for codigo, _etiqueta, _posicion in modulo.TALLAS_INICIALES}


TALLAS_DEL_ESQUEMA = _tallas_de_la_migracion()


def test_cada_talla_del_esquema_tiene_sufijo_de_sku():
    # Si se agrega una talla a la migración y no aquí, la siembra falla.
    assert TALLAS_DEL_ESQUEMA <= set(SUFIJO_SKU_POR_TALLA)


def test_la_talla_unica_produce_un_sku_sin_tilde():
    sku = _construir_sku("TL-ART-001", "ÚNICA")
    assert sku == "TL-ART-001-UNI"
    assert FORMATO_SKU.match(sku)


def test_una_talla_sin_sufijo_detiene_la_siembra():
    with pytest.raises(SystemExit):
        _construir_sku("TL-CAM-001", "XXXL")


def test_todos_los_sku_del_catalogo_cumplen_el_formato_y_son_unicos():
    skus = [
        _construir_sku(producto["sku"], talla)
        for producto in PRODUCTOS
        for talla, _unidades, _activa in producto["variantes"]
    ]
    assert all(FORMATO_SKU.match(sku) for sku in skus)
    assert len(skus) == len(set(skus))


def test_todas_las_tallas_usadas_existen_en_el_esquema():
    usadas = {talla for p in PRODUCTOS for talla, _u, _a in p["variantes"]}
    assert usadas <= TALLAS_DEL_ESQUEMA


def test_slugs_validos_y_unicos():
    slugs = [p["slug"] for p in PRODUCTOS] + [slug for _n, slug in CATEGORIAS]
    assert all(FORMATO_SLUG.match(s) for s in slugs)
    assert len(slugs) == len(set(slugs))


def test_hay_doce_productos_publicados_con_imagen():
    # Precondición de CP-80 (RNF-01): doce productos publicados con imagen.
    publicados_con_imagen = [p for p in PRODUCTOS if p["published"] and p["imagenes"]]
    assert len(publicados_con_imagen) == 12


def test_toda_imagen_tiene_texto_alternativo_real():
    # RNF-03 / CP-81: texto alternativo, no de relleno.
    textos = [alt for p in PRODUCTOS for _archivo, alt, _ancho, _alto in p["imagenes"]]
    assert all(len(alt.strip()) >= 15 for alt in textos)
    assert len(textos) == len(set(textos))


def test_los_estados_de_prueba_estan_presentes():
    """La siembra debe incluir los casos que el catálogo tiene que mostrar."""
    def unidades(p):
        return [u for _t, u, activa in p["variantes"] if activa]

    publicados = [p for p in PRODUCTOS if p["published"]]
    # Mixto: alguna talla agotada y alguna disponible (CA-01-3).
    assert any(0 in unidades(p) and any(unidades(p)) for p in publicados)
    # Publicado con todas las tallas en cero (CA-01-4, CP-06).
    assert any(unidades(p) and not any(unidades(p)) for p in publicados)
    # Sin publicar, con variantes activas (CP-03).
    assert any(not p["published"] and unidades(p) for p in PRODUCTOS)
