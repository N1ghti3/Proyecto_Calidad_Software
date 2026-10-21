"""Suite de calidad de la Entrega 2 (sección 9.2, casos PRB-01 a PRB-09), contra el sistema vivo.

Reproduce los nueve casos del documento sobre la implementación actual
(FastAPI + PostgreSQL). Los casos originales se escribieron para el prototipo
v0.2.0 (Node, `/api/productos`); aquí se conservan el requisito, el criterio y
el resultado esperado de cada uno, y cambia solo la forma de invocar el sistema.

Principios que se respetan del documento (9.1):
- cada caso declara el requisito que verifica, el resultado esperado y el obtenido;
- la suite termina con código distinto de cero si algún caso falla;
- el grupo de control (PRB-03) demuestra que el defecto prevenido existe.

Uso, con la API en marcha y la base sembrada:

    ADMIN_EMAIL=... ADMIN_PASSWORD=... python tests/calidad/suite_calidad.py [reporte.json]

Crea dos productos de prueba (prefijo «Calidad PRB») y los deja despublicados
al terminar. Las órdenes usan el dominio reservado `ejemplo.test`.
"""

from __future__ import annotations

import datetime
import json
import os
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "backend"))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from app.core.config import obtener_settings  # noqa: E402

API = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")
COMPRADOR = {"name": "Comprador de calidad", "email": "calidad@ejemplo.test",
             "phone": "3001112233", "address": "Calle de prueba 1", "city": "Bogotá D.C."}

resultados: list[dict] = []


def caso(id_: str, requisito: str, verifica: str, esperado: str):
    """Registra el caso con su resultado; una excepción cuenta como fallo."""
    def decorador(fn):
        def ejecutar(*a):
            inicio = time.perf_counter()
            try:
                obtenido, ok = fn(*a)
            except Exception as e:  # noqa: BLE001
                obtenido, ok = f"Error al ejecutar: {type(e).__name__}: {e}", False
            resultados.append({
                "caso": id_, "requisito": requisito, "verifica": verifica, "esperado": esperado,
                "obtenido": obtenido, "estado": "APROBADA" if ok else "FALLIDA",
                "duracion_ms": round((time.perf_counter() - inicio) * 1000),
            })
            print(f"{'APROBADA' if ok else 'FALLIDA ':8} {id_}  {obtenido}")
        return ejecutar
    return decorador


# ---------------------------------------------------------------- utilidades

c = httpx.Client(base_url=API, timeout=60)
# Un solo cliente compartido para las cargas simultáneas. Crear uno por
# petición (httpx.post) cuesta en Windows del orden de 200 ms por llamada y
# convertía la medición en un tiempo del arnés, no de la API: 50 × /health
# tardaban 12 s con clientes nuevos y 0,7 s con uno compartido.
carga = httpx.Client(base_url=API, timeout=60, limits=httpx.Limits(max_connections=60, max_keepalive_connections=60))
motor = create_engine(obtener_settings().database_url, pool_size=60, max_overflow=10)


def admin() -> dict:
    r = c.post("/auth/login", json={"email": os.environ["ADMIN_EMAIL"], "password": os.environ["ADMIN_PASSWORD"]})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['accessToken']}"}


def unidades(slug: str) -> dict[str, int]:
    return {v["size"]: v["availableUnits"] for v in c.get(f"/products/{slug}").json()["variants"]}


def stock_bd(variant_id: str) -> int:
    with motor.connect() as cx:
        return cx.execute(text("SELECT stock_quantity FROM inventory WHERE variant_id = :v"), {"v": variant_id}).scalar_one()


def total_ordenes(h: dict) -> int:
    return c.get("/admin/orders", headers=h, params={"pageSize": 1}).json()["meta"]["totalItems"]


def pedido(lineas: list[tuple[str, int]], consentimiento: bool = True) -> dict:
    return {"items": [{"variantId": v, "quantity": q} for v, q in lineas],
            "customer": COMPRADOR, "dataProcessingConsent": consentimiento}


def crear_producto(h: dict, nombre: str, tallas: dict[str, int], publicado: bool) -> dict:
    categoria = c.get("/categories").json()[0]["id"]
    r = c.post("/admin/products", headers=h, json={
        "name": nombre, "priceCop": 10000, "categoryId": categoria, "published": publicado,
        "description": "Producto de la suite de calidad; se despublica al terminar.",
        "variants": [{"size": t, "initialStock": n} for t, n in tallas.items()],
    })
    r.raise_for_status()
    return r.json()


# --------------------------------------------------------------------- casos

@caso("PRB-01", "REQ-01", "El catálogo expone solo productos publicados",
      "El borrador no aparece en el listado ni en el detalle (404); publicados visibles = publicados en el panel")
def prb01(h, borrador):
    publicos, pagina = [], 1
    while True:
        r = c.get("/products", params={"page": pagina, "pageSize": 50}).json()
        publicos += r["items"]
        if pagina >= r["meta"]["totalPages"]:
            break
        pagina += 1
    admin_pub = [p for p in c.get("/admin/products", headers=h, params={"pageSize": 50, "published": "true"}).json()["items"]]
    p2 = c.get("/admin/products", headers=h, params={"pageSize": 50, "published": "true", "page": 2}).json()["items"]
    admin_pub += p2
    en_listado = any(p["id"] == borrador["id"] for p in publicos)
    detalle = c.get(f"/products/{borrador['slug']}").status_code
    ok = not en_listado and detalle == 404 and len(publicos) == len(admin_pub)
    return (f"{len(publicos)} publicados visibles (panel: {len(admin_pub)}); borrador en listado: "
            f"{'sí' if en_listado else 'no'}; detalle del borrador: {detalle}"), ok


def _carga_api(variant_id: str, n: int) -> tuple[list[int], float]:
    barrera = threading.Barrier(n)

    def comprar(_):
        barrera.wait()
        try:
            return carga.post("/orders", json=pedido([(variant_id, 1)])).status_code
        except httpx.HTTPError:
            return 0
    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=n) as ex:
        codigos = list(ex.map(comprar, range(n)))
    return codigos, (time.perf_counter() - inicio) * 1000


@caso("PRB-02", "RNF-02", "50 solicitudes simultáneas sobre 10 unidades, por la API (implementación con bloqueo)",
      "10 confirmadas / 40 rechazadas con INSUFFICIENT_STOCK / stock final 0 / 0 errores")
def prb02(h, prod):
    vid = next(v["id"] for v in prod["variants"] if v["size"] == "XS")
    codigos, ms = _carga_api(vid, 50)
    confirmadas, rechazadas = codigos.count(201), codigos.count(409)
    errores = len(codigos) - confirmadas - rechazadas
    final = stock_bd(vid)
    auditadas = c.get("/admin/audit-logs", headers=h, params={"entityId": vid, "source": "ORDEN", "pageSize": 50}).json()["meta"]["totalItems"]
    ok = (confirmadas, rechazadas, final, errores, auditadas) == (10, 40, 0, 0, 10)
    return (f"{confirmadas} confirmadas, {rechazadas} rechazadas, stock final {final}, {errores} errores, "
            f"{auditadas} descuentos auditados ({ms:.0f} ms)"), ok


def _carga_bd(variant_id: str, n: int, con_bloqueo: bool) -> tuple[int, int, int]:
    """La transacción de compra reducida a su núcleo, directamente en la base.

    Igual en ambos modos salvo `FOR UPDATE`. La espera de 15 ms entre leer y
    escribir es la del documento: amplía la ventana de carrera y vuelve el
    defecto determinista; no cambia su naturaleza, solo su frecuencia.
    """
    barrera = threading.Barrier(n)
    consulta = "SELECT stock_quantity FROM inventory WHERE variant_id = :v" + (" FOR UPDATE" if con_bloqueo else "")

    def comprar(_):
        barrera.wait()
        with motor.begin() as cx:
            leido = cx.execute(text(consulta), {"v": variant_id}).scalar_one()
            time.sleep(0.015)
            if leido < 1:
                return False
            cx.execute(text("UPDATE inventory SET stock_quantity = :s WHERE variant_id = :v"),
                       {"s": leido - 1, "v": variant_id})
            return True
    with ThreadPoolExecutor(max_workers=n) as ex:
        confirmadas = sum(ex.map(comprar, range(n)))
    return confirmadas, n - confirmadas, stock_bd(variant_id)


@caso("PRB-03", "RNF-02", "Misma carga (50 sobre 10) SIN bloqueo de fila: grupo de control, comparado con el mismo arnés CON bloqueo",
      "Sin bloqueo se reproduce la sobreventa; con bloqueo, 10 / 40 / 0")
def prb03(h, prod):
    con = next(v["id"] for v in prod["variants"] if v["size"] == "XL")
    sin = next(v["id"] for v in prod["variants"] if v["size"] == "XXL")
    c1, r1, f1 = _carga_bd(con, 50, True)
    c2, r2, f2 = _carga_bd(sin, 50, False)
    ok = (c1, r1, f1) == (10, 40, 0) and c2 > 10
    return (f"CON bloqueo: {c1} confirmadas, {r1} rechazadas, stock final {f1} · SIN bloqueo: {c2} confirmadas "
            f"sobre 10 unidades (sobreventa de {c2 - 10}), stock final {f2}"), ok


@caso("PRB-04", "REQ-08", "Se rechaza la orden sin autorización de tratamiento de datos (Ley 1581 de 2012)",
      "400 CONSENT_REQUIRED; ninguna orden creada; inventario intacto")
def prb04(h, prod):
    vid = next(v["id"] for v in prod["variants"] if v["size"] == "S")
    antes, ordenes = stock_bd(vid), total_ordenes(h)
    r = c.post("/orders", json=pedido([(vid, 1)], consentimiento=False))
    sin = c.post("/orders", json={k: v for k, v in pedido([(vid, 1)]).items() if k != "dataProcessingConsent"})
    ok = (r.status_code == 400 and r.json()["error"]["code"] == "CONSENT_REQUIRED" and sin.status_code == 400
          and total_ordenes(h) == ordenes and stock_bd(vid) == antes)
    return (f"{r.status_code} {r.json()['error']['code']}; sin el campo: {sin.status_code}; órdenes nuevas: "
            f"{total_ordenes(h) - ordenes}; stock {antes}→{stock_bd(vid)}"), ok


@caso("PRB-05", "REQ-02", "Se rechaza una cantidad mayor a la existencia y no se altera el inventario",
      "Rechazo: solicitado 5, disponible 3; stock intacto en 3")
def prb05(h, prod):
    vid = next(v["id"] for v in prod["variants"] if v["size"] == "S")
    r = c.post("/orders", json=pedido([(vid, 5)]))
    linea = r.json()["error"]["details"]["items"][0] if r.status_code == 409 else {}
    final = stock_bd(vid)
    ok = r.status_code == 409 and linea.get("requestedQuantity") == 5 and linea.get("availableUnits") == 3 and final == 3
    return (f"{r.status_code} {r.json()['error']['code']}: solicitado {linea.get('requestedQuantity')}, "
            f"disponible {linea.get('availableUnits')}; stock final {final}"), ok


@caso("PRB-06", "REQ-03", "Atomicidad: si un ítem del carrito falla, no se descuenta ningún otro ni se crea la orden",
      "409 INSUFFICIENT_STOCK; stock del ítem válido sin cambios; sin orden nueva")
def prb06(h, prod):
    m = next(v["id"] for v in prod["variants"] if v["size"] == "M")
    l = next(v["id"] for v in prod["variants"] if v["size"] == "L")
    antes_m, ordenes = stock_bd(m), total_ordenes(h)
    r = c.post("/orders", json=pedido([(m, 1), (l, 2)]))
    ok = r.status_code == 409 and stock_bd(m) == antes_m and total_ordenes(h) == ordenes
    return (f"{r.status_code} {r.json()['error']['code']}; ítem válido {antes_m}→{stock_bd(m)}; "
            f"órdenes nuevas: {total_ordenes(h) - ordenes}"), ok


@caso("PRB-07", "REQ-06", "Toda variación de existencias deja registro de auditoría con origen y referencia",
      "Registro 5→3, origen ORDEN, referencia igual al código de la orden")
def prb07(h, prod):
    m = next(v["id"] for v in prod["variants"] if v["size"] == "M")
    r = c.post("/orders", json=pedido([(m, 2)]))
    r.raise_for_status()
    numero = r.json()["orderNumber"]
    a = c.get("/admin/audit-logs", headers=h, params={"entityId": m, "pageSize": 1}).json()["items"][0]
    referencia = numero in json.dumps(a, ensure_ascii=False)
    ok = (a["oldValue"], a["newValue"], a["source"]) == ("5", "3", "ORDEN") and referencia
    return (f"Registro {a['oldValue']}→{a['newValue']}, origen {a['source']}; referencia a {numero}: "
            f"{'presente' if referencia else 'AUSENTE (el registro no guarda el código de la orden)'}"), ok


@caso("PRB-08", "REQ-03", "Se rechaza un carrito vacío", "400 VALIDATION_ERROR en la orden y en la validación del carrito")
def prb08(h, prod):
    r = c.post("/orders", json={"items": [], "customer": COMPRADOR, "dataProcessingConsent": True})
    v = c.post("/cart/validate", json={"items": []})
    campo = r.json()["error"]["details"]["fields"][0]["field"] if r.status_code == 400 else None
    ok = r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR" and campo == "items" and v.status_code == 400
    return f"Orden: {r.status_code} {r.json()['error']['code']} (campo {campo}); validación del carrito: {v.status_code}", ok


@caso("PRB-09", "RNF-02", "La restricción CHECK (stock >= 0) impide un inventario negativo",
      "La base rechaza la escritura con código 23514; la API responde 400")
def prb09(h, prod):
    vid = next(v["id"] for v in prod["variants"] if v["size"] == "S")
    codigo = None
    try:
        with motor.begin() as cx:
            cx.execute(text("UPDATE inventory SET stock_quantity = -1 WHERE variant_id = :v"), {"v": vid})
    except IntegrityError as e:
        codigo = getattr(e.orig, "sqlstate", None)
    api = c.patch(f"/admin/variants/{vid}/inventory", headers=h, json={"stockQuantity": -1, "reason": "Prueba PRB-09"})
    ok = codigo == "23514" and api.status_code == 400 and stock_bd(vid) == 3
    return f"Base de datos: rechazo con código {codigo}; API: {api.status_code}; stock intacto en {stock_bd(vid)}", ok


@caso("PRB-10", "RNF-02 (adicional)", "Sin interbloqueos: 40 órdenes simultáneas con las mismas dos tallas en orden alterno",
      "40 confirmadas, 0 errores 500 (el bloqueo se toma ordenado por variant_id, defecto 1 de la sección 9.2)")
def prb10(h, prod2):
    a, b = (v["id"] for v in prod2["variants"][:2])
    barrera = threading.Barrier(40)

    def comprar(i):
        barrera.wait()
        lineas = [(a, 1), (b, 1)] if i % 2 else [(b, 1), (a, 1)]
        try:
            return carga.post("/orders", json=pedido(lineas)).status_code
        except httpx.HTTPError:
            return 0
    with ThreadPoolExecutor(max_workers=40) as ex:
        codigos = list(ex.map(comprar, range(40)))
    ok = codigos.count(201) == 40
    return f"{codigos.count(201)} confirmadas, {sum(1 for x in codigos if x >= 500 or x == 0)} errores", ok


# ---------------------------------------------------------------- ejecución

def main() -> int:
    h = admin()
    marca = uuid.uuid4().hex[:6]
    prod = crear_producto(h, f"Calidad PRB {marca}",
                          {"XS": 10, "S": 3, "M": 5, "L": 1, "XL": 10, "XXL": 10}, publicado=True)
    prod2 = crear_producto(h, f"Calidad PRB interbloqueo {marca}", {"S": 100, "M": 100}, publicado=True)
    borrador = crear_producto(h, f"Calidad PRB borrador {marca}", {"M": 1}, publicado=False)
    try:
        prb01(h, borrador)
        prb02(h, prod)
        prb03(h, prod)
        prb04(h, prod)
        prb05(h, prod)
        prb06(h, prod)
        prb07(h, prod)
        prb08(h, prod)
        prb09(h, prod)
        prb10(h, prod2)
    finally:
        for p in (prod, prod2):
            c.patch(f"/admin/products/{p['id']}", headers=h, json={"published": False})

    aprobadas = sum(r["estado"] == "APROBADA" for r in resultados)
    reporte = {
        "ejecutado": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "api": API, "total": len(resultados), "aprobadas": aprobadas,
        "fallidas": len(resultados) - aprobadas, "casos": resultados,
    }
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "docs" / "pruebas" / "resultados-calidad.json"
    destino.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nTotal: {len(resultados)} casos, {aprobadas} aprobados, {len(resultados) - aprobadas} fallidos -> {destino}")
    return 0 if aprobadas == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
