"""Regresiones del contrato de la API, contra el servicio real.

Cada prueba corresponde a un defecto encontrado al probar la rama
`feat/sistema-completo` de punta a punta. Se escriben contra la API viva, como
`tests/concurrency/test_api_concurrente.py`, porque varios de esos defectos
solo aparecían al serializar la respuesta: la consulta pública de una orden
respondía 500 aunque la lógica de la ruta fuera correcta.

Uso:

    # con la API corriendo en localhost:8000 y la base sembrada
    ADMIN_EMAIL=... ADMIN_PASSWORD=... pytest tests/api -v

Sin ADMIN_EMAIL y ADMIN_PASSWORD las pruebas del panel se omiten.

Ojo con el límite de inicio de sesión: cada corrida suma 5 intentos fallidos a
la dirección local. Más de tres corridas seguidas dentro del mismo minuto
agotan el límite por IP (20) y el inicio de sesión del panel responde 429.
"""

from __future__ import annotations

import os
import uuid

import httpx
import pytest

API = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

COMPRADOR = {
    "name": "Comprador de contrato",
    "email": "Contrato.Prueba@Ejemplo.test",
    "phone": "+57 300 123 4567",
    "address": "Calle de prueba 123",
    "city": "Bogotá D.C.",
}


@pytest.fixture(scope="module")
def api_viva() -> None:
    try:
        salud = httpx.get(f"{API}/health", timeout=5).json()
    except httpx.HTTPError:
        pytest.skip(f"La API no responde en {API}")
    if salud.get("database") != "ok":
        pytest.skip("La API responde pero no alcanza la base de datos")


@pytest.fixture(scope="module")
def admin(api_viva) -> dict:
    if not (ADMIN_EMAIL and ADMIN_PASSWORD):
        pytest.skip("Defina ADMIN_EMAIL y ADMIN_PASSWORD para probar el panel")
    r = httpx.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=10)
    assert r.status_code == 200, r.text
    return r.json()


def _cabeceras(sesion: dict) -> dict:
    return {"Authorization": f"Bearer {sesion['accessToken']}"}


def _variante_con_stock(minimo: int = 2) -> tuple[str, int, int, str]:
    """(variantId, unidades, precio, slug) de una variante con al menos `minimo` unidades."""
    r = httpx.get(f"{API}/products", params={"pageSize": 50, "inStock": True}, timeout=10)
    r.raise_for_status()
    for resumen in r.json()["items"]:
        detalle = httpx.get(f"{API}/products/{resumen['slug']}", timeout=10).json()
        for v in detalle["variants"]:
            if v["availableUnits"] >= minimo:
                return v["id"], v["availableUnits"], detalle["priceCop"], resumen["slug"]
    pytest.skip(f"No hay variantes con {minimo} o más unidades")


def _unidades(slug: str, variant_id: str) -> int:
    detalle = httpx.get(f"{API}/products/{slug}", timeout=10).json()
    return next(v["availableUnits"] for v in detalle["variants"] if v["id"] == variant_id)


def _pedido(variant_id: str, **extra) -> dict:
    return {
        "items": [{"variantId": variant_id, "quantity": 1}],
        "customer": COMPRADOR,
        "dataProcessingConsent": True,
        **extra,
    }


# ---------------------------------------------------------------- compra


def test_la_consulta_publica_de_una_orden_responde_enmascarada(api_viva) -> None:
    """EP-06 respondía siempre 500: el teléfono enmascarado no pasaba el
    validador del modelo de entrada con que se armaba la respuesta."""
    variant_id, _, precio, _ = _variante_con_stock()
    creada = httpx.post(f"{API}/orders", json=_pedido(variant_id), timeout=10)
    assert creada.status_code == 201, creada.text
    numero = creada.json()["orderNumber"]

    r = httpx.get(f"{API}/orders/{numero}", params={"email": COMPRADOR["email"]}, timeout=10)

    assert r.status_code == 200, r.text
    cliente = r.json()["customer"]
    assert cliente["email"] == "c***@ejemplo.test"
    assert cliente["phone"].endswith("4567") and "*" in cliente["phone"]
    assert r.json()["items"][0]["lineTotalCop"] == precio


def test_un_campo_desconocido_se_rechaza_sin_crear_la_orden(api_viva) -> None:
    """convenciones.md, regla 3. Antes `{"extra": 1}` pasaba y creaba la orden."""
    variant_id, unidades, _, slug = _variante_con_stock()

    r = httpx.post(f"{API}/orders", json=_pedido(variant_id, extra=1), timeout=10)

    assert r.status_code == 400
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert {"field": "extra", "issue": "Extra inputs are not permitted"} in r.json()["error"]["details"]["fields"]
    assert _unidades(slug, variant_id) == unidades, "la petición rechazada descontó inventario"


def test_la_validacion_del_carrito_trae_total_y_fecha(api_viva) -> None:
    """CartValidationResponse exige `totalCop` y `checkedAt` (modelos.md)."""
    variant_id, _, precio, _ = _variante_con_stock()

    r = httpx.post(f"{API}/cart/validate", json={"items": [{"variantId": variant_id, "quantity": 2}]}, timeout=10)

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["valid"] is True
    assert cuerpo["totalCop"] == 2 * precio
    assert cuerpo["checkedAt"]


# ---------------------------------------------------------------- panel


def test_el_inicio_de_sesion_devuelve_el_usuario(admin) -> None:
    assert admin["tokenType"] == "Bearer"
    assert admin["user"]["email"] == ADMIN_EMAIL.lower()
    assert admin["user"]["fullName"]


def test_el_ajuste_de_inventario_usa_stock_quantity_y_queda_auditado(admin) -> None:
    """El panel enviaba `availableUnits` y el backend esperaba `stockQuantity`:
    ningún ajuste desde la interfaz llegaba a guardarse."""
    h = _cabeceras(admin)
    fila = httpx.get(f"{API}/admin/inventory", headers=h, params={"pageSize": 1}, timeout=10).json()["items"][0]
    original = fila["stockQuantity"]
    ruta = f"{API}/admin/variants/{fila['variantId']}/inventory"

    mal = httpx.patch(ruta, headers=h, json={"availableUnits": original + 1, "reason": "Prueba"}, timeout=10)
    assert mal.status_code == 400

    try:
        r = httpx.patch(ruta, headers=h, json={"stockQuantity": original + 1, "reason": "Prueba de contrato"}, timeout=10)
        assert r.status_code == 200, r.text
        assert r.json()["stockQuantity"] == original + 1
        assert r.json()["updatedAt"]

        auditoria = httpx.get(
            f"{API}/admin/audit-logs", headers=h,
            params={"entityId": fila["variantId"], "pageSize": 1}, timeout=10,
        ).json()["items"][0]
        assert auditoria["newValue"] == str(original + 1)
        assert auditoria["performedBy"] == admin["user"]["fullName"]
    finally:
        httpx.patch(ruta, headers=h, json={"stockQuantity": original, "reason": "Restaurar tras prueba"}, timeout=10)


def test_publicar_exige_un_booleano(admin) -> None:
    """EP-13 recibía un `dict` sin validar: `{"published": "quizá"}` publicaba."""
    h = _cabeceras(admin)
    producto = httpx.get(f"{API}/admin/products", headers=h, params={"pageSize": 1}, timeout=10).json()["items"][0]

    r = httpx.patch(f"{API}/admin/products/{producto['id']}/publish", headers=h, json={"published": "quizá"}, timeout=10)

    assert r.status_code == 400
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_los_intentos_fallidos_se_limitan_por_cuenta(api_viva) -> None:
    """contrato-api.md: 5 intentos por minuto y por cuenta (OWASP A07)."""
    correo = f"nadie-{uuid.uuid4().hex[:8]}@ejemplo.test"
    for _ in range(5):
        r = httpx.post(f"{API}/auth/login", json={"email": correo, "password": "incorrecta-123"}, timeout=10)
        assert r.status_code == 401

    r = httpx.post(f"{API}/auth/login", json={"email": correo, "password": "incorrecta-123"}, timeout=10)

    assert r.status_code == 429
    assert r.json()["error"]["code"] == "RATE_LIMITED"
    assert int(r.headers["Retry-After"]) > 0
    assert r.json()["error"]["details"]["retryAfterSeconds"] == int(r.headers["Retry-After"])
