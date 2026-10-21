"""Alta y edición de productos (EP-12, EP-14, EP-16, EP-22, EP-25), contra la API viva.

Uso igual que `test_contrato.py`:

    ADMIN_EMAIL=... ADMIN_PASSWORD=... pytest tests/api -v

Cada corrida crea productos de prueba con un sufijo aleatorio. El contrato no
tiene borrado de productos (RN-23), así que se dejan **despublicados** al
terminar: no aparecen en la tienda, pero sí en el panel.
"""

from __future__ import annotations

import io
import os
import uuid

import httpx
import pytest

API = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")
ORIGEN = API.rsplit("/api/", 1)[0]
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


@pytest.fixture(scope="module")
def h() -> dict:
    try:
        httpx.get(f"{API}/health", timeout=5)
    except httpx.HTTPError:
        pytest.skip(f"La API no responde en {API}")
    if not (ADMIN_EMAIL and ADMIN_PASSWORD):
        pytest.skip("Defina ADMIN_EMAIL y ADMIN_PASSWORD para probar el panel")
    r = httpx.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=10)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['accessToken']}"}


@pytest.fixture(scope="module")
def categoria() -> dict:
    return httpx.get(f"{API}/categories", timeout=10).json()[0]


def _nuevo(categoria: dict, **extra) -> dict:
    return {
        "name": f"Gorra de prueba Ñandú {uuid.uuid4().hex[:6]}",
        "description": "  Bordada a mano.  ",
        "priceCop": 45000,
        "categoryId": categoria["id"],
        "variants": [{"size": "m", "initialStock": 4}, {"size": "L", "initialStock": 0}],
        **extra,
    }


@pytest.fixture(scope="module")
def creado(h, categoria) -> dict:
    r = httpx.post(f"{API}/admin/products", headers=h, json=_nuevo(categoria), timeout=10)
    assert r.status_code == 201, r.text
    return r.json()


def _png(ancho: int, alto: int) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (ancho, alto), (200, 80, 40)).save(buf, "PNG")
    return buf.getvalue()


# ------------------------------------------------------------------- EP-12


def test_crear_genera_slug_y_sku_y_nace_despublicado(creado) -> None:
    assert creado["slug"].startswith("gorra-de-prueba-nandu-")
    assert creado["published"] is False
    assert creado["description"] == "Bordada a mano."
    tallas = {v["size"]: v for v in creado["variants"]}
    assert set(tallas) == {"M", "L"}  # la talla se normaliza a mayúsculas
    assert tallas["M"]["availableUnits"] == 4 and tallas["L"]["inStock"] is False
    base = {v["sku"].rsplit("-", 1)[0] for v in creado["variants"]}
    assert len(base) == 1 and base.pop().startswith("TL-")
    # RN-01: despublicado no existe para el público.
    assert httpx.get(f"{API}/products/{creado['slug']}", timeout=10).status_code == 404


def test_las_existencias_iniciales_quedan_auditadas(h, creado) -> None:
    """RN-24: también el inventario con que nace una talla."""
    m = next(v for v in creado["variants"] if v["size"] == "M")
    entrada = httpx.get(f"{API}/admin/audit-logs", headers=h, params={"entityId": m["id"]}, timeout=10).json()["items"][0]
    assert (entrada["action"], entrada["source"], entrada["oldValue"], entrada["newValue"]) == (
        "STOCK_CHANGE", "AJUSTE_MANUAL", None, "4")
    assert entrada["performedBy"]


def test_el_detalle_del_panel_lee_productos_despublicados(h, creado) -> None:
    r = httpx.get(f"{API}/admin/products/{creado['id']}", headers=h, timeout=10)
    assert r.status_code == 200 and r.json()["id"] == creado["id"]


@pytest.mark.parametrize("cambio, codigo, campo", [
    ({"variants": [{"size": "XXXL", "initialStock": 1}]}, 400, "variants.0.size"),
    ({"variants": [{"size": "M", "initialStock": 1}, {"size": "m", "initialStock": 2}]}, 409, "size"),
    ({"variants": [{"size": "M", "initialStock": 1, "active": False}], "published": True}, 400, "published"),
    ({"priceCop": 0}, 400, "priceCop"),
    ({"categoryId": str(uuid.uuid4())}, 400, "categoryId"),
    ({"variants": [{"size": "M", "initialStock": 1, "sku": "con espacios"}]}, 400, "variants.0.sku"),
])
def test_crear_rechaza_datos_invalidos(h, categoria, cambio, codigo, campo) -> None:
    r = httpx.post(f"{API}/admin/products", headers=h, json=_nuevo(categoria, **cambio), timeout=10)
    assert r.status_code == codigo, r.text
    error = r.json()["error"]
    campos = [f["field"] for f in error["details"].get("fields", [])] or [error["details"].get("field")]
    assert campo in campos


def test_sin_token_no_se_crea_nada(categoria) -> None:
    r = httpx.post(f"{API}/admin/products", json=_nuevo(categoria), timeout=10)
    assert r.status_code == 401


# ------------------------------------------------------------------- EP-14


def test_agregar_talla_reutiliza_la_base_del_sku(h, creado) -> None:
    r = httpx.post(f"{API}/admin/products/{creado['id']}/variants", headers=h,
                   json={"size": "XL", "initialStock": 2}, timeout=10)
    assert r.status_code == 201, r.text
    base = creado["variants"][0]["sku"].rsplit("-", 1)[0]
    assert r.json()["sku"] == f"{base}-XL" and r.json()["availableUnits"] == 2

    repetida = httpx.post(f"{API}/admin/products/{creado['id']}/variants", headers=h,
                          json={"size": "xl", "initialStock": 1}, timeout=10)
    assert repetida.status_code == 409 and repetida.json()["error"]["code"] == "CONFLICT"

    inexistente = httpx.post(f"{API}/admin/products/{uuid.uuid4()}/variants", headers=h,
                             json={"size": "S", "initialStock": 1}, timeout=10)
    assert inexistente.status_code == 404


# ------------------------------------------------------------------- EP-22


def test_editar_aplica_solo_lo_enviado_y_conserva_el_slug(h, creado) -> None:
    r = httpx.patch(f"{API}/admin/products/{creado['id']}", headers=h,
                    json={"name": "Gorra renombrada", "priceCop": 52000}, timeout=10)
    assert r.status_code == 200, r.text
    p = r.json()
    assert (p["name"], p["priceCop"]) == ("Gorra renombrada", 52000)
    assert p["description"] == creado["description"]  # no se envió: no cambia
    assert p["slug"] == creado["slug"]  # los enlaces ya compartidos siguen sirviendo


def test_editar_rechaza_nulos_y_variantes(h, creado) -> None:
    nulo = httpx.patch(f"{API}/admin/products/{creado['id']}", headers=h, json={"name": None}, timeout=10)
    assert nulo.status_code == 400
    variantes = httpx.patch(f"{API}/admin/products/{creado['id']}", headers=h,
                            json={"variants": []}, timeout=10)
    assert variantes.status_code == 400  # las tallas se agregan por EP-14


def test_publicar_desde_la_edicion_lo_muestra_en_la_tienda(h, creado) -> None:
    ruta = f"{API}/admin/products/{creado['id']}"
    try:
        assert httpx.patch(ruta, headers=h, json={"published": True}, timeout=10).status_code == 200
        assert httpx.get(f"{API}/products/{creado['slug']}", timeout=10).status_code == 200
    finally:
        httpx.patch(ruta, headers=h, json={"published": False}, timeout=10)


# ------------------------------------------------------------------- EP-16


def test_la_imagen_se_redimensiona_y_se_sirve_en_webp(h, creado) -> None:
    r = httpx.post(f"{API}/admin/products/{creado['id']}/images", headers=h,
                   files={"file": ("foto.png", _png(2400, 1200), "image/png")},
                   data={"alt": "Gorra naranja vista de frente"}, timeout=30)
    assert r.status_code == 201, r.text
    img = r.json()
    assert (img["width"], img["height"]) == (1200, 600)
    assert img["url"].startswith("/media/cargas/") and img["url"].endswith(".webp")

    servida = httpx.get(ORIGEN + img["url"], timeout=10)
    assert servida.status_code == 200
    assert servida.headers["content-type"] == "image/webp"

    detalle = httpx.get(f"{API}/admin/products/{creado['id']}", headers=h, timeout=10).json()
    assert detalle["images"][0]["alt"] == "Gorra naranja vista de frente"


def test_la_posicion_ocupada_es_conflicto(h, creado) -> None:
    r = httpx.post(f"{API}/admin/products/{creado['id']}/images", headers=h,
                   files={"file": ("foto.png", _png(100, 100), "image/png")},
                   data={"alt": "Otra", "position": "0"}, timeout=30)
    assert r.status_code == 409


def test_sin_texto_alternativo_no_se_acepta(h, creado) -> None:
    """RNF-03: una foto sin descripción es invisible para un lector de pantalla."""
    r = httpx.post(f"{API}/admin/products/{creado['id']}/images", headers=h,
                   files={"file": ("foto.png", _png(100, 100), "image/png")}, timeout=30)
    assert r.status_code == 400
    assert r.json()["error"]["details"]["fields"][0]["field"] == "alt"


def test_un_archivo_que_no_es_imagen_se_rechaza_aunque_diga_serlo(h, creado) -> None:
    r = httpx.post(f"{API}/admin/products/{creado['id']}/images", headers=h,
                   files={"file": ("foto.png", b"esto no es una imagen", "image/png")},
                   data={"alt": "Falsa"}, timeout=30)
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"
    assert "image/webp" in r.json()["error"]["details"]["allowed"]


def test_un_archivo_demasiado_grande_se_rechaza(h, creado) -> None:
    r = httpx.post(f"{API}/admin/products/{creado['id']}/images", headers=h,
                   files={"file": ("grande.png", b"0" * (5 * 1024 * 1024 + 1), "image/png")},
                   data={"alt": "Grande"}, timeout=60)
    assert r.status_code == 413
    assert r.json()["error"]["details"]["maxBytes"] == 5 * 1024 * 1024
