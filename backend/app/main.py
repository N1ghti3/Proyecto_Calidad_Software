"""Aplicación FastAPI de TiendaLocal.

Monta los routers bajo `/api/v1` (ADR-004: la versión va en la ruta, no en una
cabecera, para que un cliente antiguo siga funcionando cuando exista /api/v2).

Dos piezas transversales viven aquí:

**`X-Request-Id`.** Se asigna al entrar y acompaña a toda respuesta, correcta o
no, y a toda línea del registro. Cuando alguien informa un fallo, ese
identificador es lo único que hace falta para encontrar la petición exacta.

**CORS.** En desarrollo el frontend corre en el puerto 5173 y la API en el
8000; sin esto el navegador bloquea toda petición antes de que salga. Los
orígenes se declaran explícitos y nunca `*`: con credenciales, el comodín es
una invitación abierta.
"""

from __future__ import annotations

import logging
import secrets

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import errores
from app.api.v1 import administracion, autenticacion, catalogo, compra
from app.core.config import obtener_settings
from app.db.sesion import motor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
registro = logging.getLogger("tiendalocal.api")

PREFIJO = "/api/v1"

app = FastAPI(
    title="TiendaLocal — API",
    version="1.1.0",
    description=(
        "Catálogo, checkout simulado y panel de administración.\n\n"
        "Contrato: docs/api/. El pago es simulado (RN-12): el sistema nunca "
        "manipula datos financieros, de modo que PCI DSS no le aplica."
    ),
    docs_url=f"{PREFIJO}/docs",
    openapi_url=f"{PREFIJO}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in obtener_settings().cors_origenes.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    expose_headers=["X-Request-Id"],
)


@app.middleware("http")
async def identificar_peticion(peticion: Request, siguiente):
    """Asigna el identificador antes de cualquier otra cosa.

    Se respeta el que venga del proxy si existe: así una petición conserva el
    mismo identificador en los registros de nginx y en los de la aplicación, y
    seguir su rastro no exige correlacionar por marca de tiempo.
    """
    id_peticion = peticion.headers.get("X-Request-Id") or f"req_{secrets.token_hex(6)}"
    peticion.state.id_peticion = id_peticion
    respuesta = await siguiente(peticion)
    respuesta.headers["X-Request-Id"] = id_peticion
    return respuesta


errores.registrar_manejadores(app)

for enrutador in (catalogo.router, compra.router, autenticacion.router, administracion.router):
    app.include_router(enrutador, prefix=PREFIJO)


@app.get(f"{PREFIJO}/health", tags=["operación"])
def salud():
    """Verificación de salud del contenedor.

    Consulta la base en lugar de responder «ok» a secas: un proceso vivo que no
    alcanza su base de datos no está sano, y el orquestador debe reiniciarlo en
    lugar de seguir enviándole tráfico.
    """
    try:
        with motor.connect() as cx:
            cx.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception:  # noqa: BLE001
        registro.exception("Verificación de salud: la base no responde")
        return {"status": "degraded", "database": "unreachable"}
