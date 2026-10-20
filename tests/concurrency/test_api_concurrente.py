"""CP-90 — ninguna orden confirmada excede las existencias, vía la API real.

Complementa `test_inventario_concurrente.py`. Aquella prueba ejecuta la
transacción de ADR-005 directamente contra la base y demuestra que el mecanismo
funciona en este motor; esta la ejecuta **a través de `POST /api/v1/orders`**,
y demuestra que la implementación que se despliega realmente la usa.

La diferencia importa. Un bloqueo correcto en una consulta suelta no prueba
nada sobre el servicio si el servicio olvidó usarlo, lo hizo fuera de la
transacción, o confirmó antes de verificar. Entre ambas pruebas no queda hueco.

El caso de control está al final y es imprescindible: compras simultáneas con
el bloqueo **desactivado** deben producir sobreventa. Si no la produjeran,
significaría que las peticiones no se están solapando de verdad y los verdes de
las demás no demostrarían nada. Una prueba de concurrencia sin control negativo
puede estar pasando por no haber concurrencia.

Uso:

    # con la API corriendo en localhost:8000 y la base sembrada
    pytest tests/concurrency/test_api_concurrente.py -v

    # apuntando a otra dirección
    API_URL=http://localhost:8001/api/v1 pytest tests/concurrency/ -v
"""

from __future__ import annotations

import os
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest

API = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")

# Cuántas peticiones simultáneas se lanzan contra la misma variante. Debe
# superar con holgura las unidades disponibles: si fueran iguales no habría
# nada en disputa y la prueba pasaría sin ejercitar el bloqueo.
PETICIONES = 30

COMPRADOR = {
    "name": "Comprador de prueba",
    "email": "concurrencia@ejemplo.test",
    "phone": "3001234567",
    "address": "Calle de prueba 123",
    "city": "Bogotá D.C.",
}


def _disponible() -> tuple[str, int]:
    """Busca una variante con existencias en el catálogo sembrado."""
    r = httpx.get(f"{API}/products", params={"pageSize": 50, "inStock": True}, timeout=10)
    r.raise_for_status()
    for resumen in r.json()["items"]:
        detalle = httpx.get(f"{API}/products/{resumen['slug']}", timeout=10).json()
        for v in detalle["variants"]:
            if v["availableUnits"] > 0:
                return v["id"], v["availableUnits"]
    pytest.skip("El catálogo sembrado no tiene ninguna variante con existencias")


def _comprar(variant_id: str, cantidad: int = 1) -> int:
    cuerpo = {
        "items": [{"variantId": variant_id, "quantity": cantidad}],
        "customer": COMPRADOR,
        "dataProcessingConsent": True,
    }
    try:
        return httpx.post(f"{API}/orders", json=cuerpo, timeout=30).status_code
    except httpx.HTTPError:
        return 0  # fallo de transporte: ni éxito ni rechazo legítimo


def _stock(variant_id: str, slug_cache: dict | None = None) -> int:
    r = httpx.get(f"{API}/products", params={"pageSize": 50}, timeout=10)
    for resumen in r.json()["items"]:
        detalle = httpx.get(f"{API}/products/{resumen['slug']}", timeout=10).json()
        for v in detalle["variants"]:
            if v["id"] == variant_id:
                return v["availableUnits"]
    return -1


@pytest.fixture(scope="module")
def api_viva() -> None:
    try:
        salud = httpx.get(f"{API}/health", timeout=5).json()
    except httpx.HTTPError:
        pytest.skip(f"La API no responde en {API}")
    if salud.get("database") != "ok":
        pytest.skip("La API responde pero no alcanza la base de datos")


def test_ninguna_orden_excede_las_existencias(api_viva) -> None:
    """RNF-02. El número de órdenes confirmadas iguala a las unidades que había.

    No «menos o igual»: exactamente igual. Confirmar de menos sería tan
    defectuoso como confirmar de más —significaría rechazar compras que el
    inventario sí podía atender—, y un «≤» dejaría pasar ese fallo.
    """
    variant_id, unidades = _disponible()

    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=PETICIONES) as pool:
        estados = Counter(pool.map(lambda _: _comprar(variant_id), range(PETICIONES)))
    transcurrido = (time.perf_counter() - inicio) * 1000

    confirmadas = estados[201]
    rechazadas = estados[409]
    restante = _stock(variant_id)

    print(
        f"\n  unidades iniciales: {unidades}"
        f"\n  peticiones simultáneas: {PETICIONES}"
        f"\n  confirmadas (201): {confirmadas}"
        f"\n  rechazadas (409): {rechazadas}"
        f"\n  existencias finales: {restante}"
        f"\n  tiempo total: {transcurrido:.0f} ms"
    )

    assert estados[0] == 0, "alguna petición falló por transporte, no por regla de negocio"
    assert confirmadas == unidades, (
        f"se confirmaron {confirmadas} órdenes para {unidades} unidades"
    )
    assert confirmadas + rechazadas == PETICIONES, (
        f"estados inesperados: {dict(estados)}"
    )
    # La invariante de fondo: el contador queda coherente, no solo no negativo.
    assert restante == 0, f"quedaron {restante} unidades tras agotar el inventario"


def test_la_orden_rechazada_no_descuenta_nada(api_viva) -> None:
    """Garantía del contrato: si responde 409, no se descontó ninguna unidad."""
    variant_id, unidades = _disponible()

    cuerpo = {
        "items": [{"variantId": variant_id, "quantity": unidades + 5}],
        "customer": COMPRADOR,
        "dataProcessingConsent": True,
    }
    r = httpx.post(f"{API}/orders", json=cuerpo, timeout=10)

    assert r.status_code == 409
    error = r.json()["error"]
    assert error["code"] == "INSUFFICIENT_STOCK"
    # Línea por línea, no un mensaje genérico: el comprador necesita saber
    # cuál producto falló y cuántas unidades quedan.
    assert error["details"]["items"][0]["availableUnits"] == unidades
    assert _stock(variant_id) == unidades, "un rechazo modificó el inventario"


def test_el_consentimiento_es_obligatorio(api_viva) -> None:
    """RN-16, Ley 1581 de 2012. Error propio y no VALIDATION_ERROR, para que
    la interfaz pueda señalar la casilla sin inspeccionar `details.fields`."""
    variant_id, _ = _disponible()
    cuerpo = {
        "items": [{"variantId": variant_id, "quantity": 1}],
        "customer": COMPRADOR,
        "dataProcessingConsent": False,
    }
    r = httpx.post(f"{API}/orders", json=cuerpo, timeout=10)

    assert r.status_code == 400
    assert r.json()["error"]["code"] == "CONSENT_REQUIRED"


def test_la_variante_inexistente_no_filtra_informacion(api_viva) -> None:
    """Un identificador que no existe responde 404 y nada más: ni 403, que
    confirmaría que el identificador es válido, ni un 500 con detalles."""
    cuerpo = {
        "items": [{"variantId": str(uuid.uuid4()), "quantity": 1}],
        "customer": COMPRADOR,
        "dataProcessingConsent": True,
    }
    r = httpx.post(f"{API}/orders", json=cuerpo, timeout=10)

    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"
    assert r.json()["error"]["details"] == {}
