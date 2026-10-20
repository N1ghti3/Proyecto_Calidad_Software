"""Errores de la API con la forma única que exige el contrato.

`docs/api/errores.md` fija dos reglas que este módulo hace cumplir por
construcción, en lugar de confiar en que cada ruta las recuerde:

1. **Toda respuesta ≥ 400 tiene la misma estructura**: `error.code`,
   `error.message`, `error.details`, `error.requestId`. Sin excepciones, ni
   siquiera para los errores que FastAPI genera por su cuenta.

2. **El cliente decide con `code`, nunca con `message`.** Por eso los códigos
   son constantes y los mensajes son texto suelto que puede reescribirse sin
   romper a nadie.

El `requestId` viaja además en la cabecera `X-Request-Id` de toda respuesta,
también de las correctas. Cuando alguien reporta un fallo, ese identificador es
lo único que hace falta para encontrar la petición en el registro.

Sobre los 500: el mensaje que sale es siempre genérico. La traza se registra
del lado del servidor con su `requestId`. Devolver el detalle de una excepción
al cliente informa a un atacante sobre la estructura interna, y a un usuario
legítimo no le sirve de nada.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

registro = logging.getLogger("tiendalocal.api")


class ErrorApi(Exception):
    """Error de dominio que ya sabe con qué código y estado debe salir."""

    def __init__(
        self,
        codigo: str,
        mensaje: str,
        estado: int,
        detalles: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje
        self.estado = estado
        self.detalles = detalles or {}


# --------------------------------------------------------------- atajos
# Cada uno corresponde a una fila del catálogo de códigos de errores.md.


def validacion(campos: list[dict[str, str]], mensaje: str | None = None) -> ErrorApi:
    return ErrorApi(
        "VALIDATION_ERROR",
        mensaje or "La solicitud contiene campos inválidos",
        status.HTTP_400_BAD_REQUEST,
        {"fields": campos},
    )


def consentimiento_requerido() -> ErrorApi:
    """RN-16. Error propio y no VALIDATION_ERROR: el frontend debe poder
    señalar la casilla de autorización sin inspeccionar `details.fields`."""
    return ErrorApi(
        "CONSENT_REQUIRED",
        "Debe autorizar el tratamiento de datos personales para continuar",
        status.HTTP_400_BAD_REQUEST,
        {"field": "dataProcessingConsent"},
    )


def no_encontrado(mensaje: str = "El recurso solicitado no existe") -> ErrorApi:
    return ErrorApi("NOT_FOUND", mensaje, status.HTTP_404_NOT_FOUND)


def credenciales_invalidas() -> ErrorApi:
    """No distingue entre correo inexistente y contraseña incorrecta: decirlo
    permitiría enumerar cuentas válidas (OWASP A07)."""
    return ErrorApi(
        "INVALID_CREDENTIALS",
        "Correo o contraseña incorrectos",
        status.HTTP_401_UNAUTHORIZED,
    )


def no_autenticado() -> ErrorApi:
    return ErrorApi(
        "UNAUTHENTICATED",
        "Se requiere autenticación para esta operación",
        status.HTTP_401_UNAUTHORIZED,
    )


def existencias_insuficientes(items: list[dict[str, Any]]) -> ErrorApi:
    """Línea por línea, nunca un error genérico: el comprador necesita saber
    cuál de sus productos falló y cuántas unidades quedan."""
    return ErrorApi(
        "INSUFFICIENT_STOCK",
        "Algunas líneas no tienen unidades suficientes",
        status.HTTP_409_CONFLICT,
        {"items": items},
    )


def conflicto(campo: str, valor: str) -> ErrorApi:
    return ErrorApi(
        "CONFLICT",
        f"Ya existe un registro con ese valor en «{campo}»",
        status.HTTP_409_CONFLICT,
        {"field": campo, "value": valor},
    )


def transicion_invalida(actual: str, solicitado: str, permitidos: list[str]) -> ErrorApi:
    return ErrorApi(
        "INVALID_STATE_TRANSITION",
        f"No se puede pasar de {actual} a {solicitado}",
        status.HTTP_409_CONFLICT,
        {"currentStatus": actual, "requestedStatus": solicitado, "allowed": permitidos},
    )


# ------------------------------------------------------------ respuesta


def _cuerpo(
    codigo: str, mensaje: str, detalles: dict[str, Any], id_peticion: str
) -> dict[str, Any]:
    return {
        "error": {
            "code": codigo,
            "message": mensaje,
            # Objeto vacío, nunca null: el cliente puede indexarlo sin comprobar.
            "details": detalles or {},
            "requestId": id_peticion,
        }
    }


def _id_peticion(peticion: Request) -> str:
    return getattr(peticion.state, "id_peticion", "req_desconocido")


def _respuesta(peticion: Request, error: ErrorApi) -> JSONResponse:
    id_peticion = _id_peticion(peticion)
    return JSONResponse(
        status_code=error.estado,
        content=_cuerpo(error.codigo, error.mensaje, error.detalles, id_peticion),
        headers={"X-Request-Id": id_peticion},
    )


def registrar_manejadores(app: FastAPI) -> None:
    """Conecta los manejadores. Se llama una vez, al construir la aplicación."""

    @app.exception_handler(ErrorApi)
    async def _dominio(peticion: Request, exc: ErrorApi) -> JSONResponse:
        return _respuesta(peticion, exc)

    @app.exception_handler(RequestValidationError)
    async def _validacion(
        peticion: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Pydantic devuelve la ruta del campo como tupla ('body', 'customer',
        # 'email'); el contrato la quiere en notación de punto y sin el origen.
        campos = []
        for err in exc.errors():
            partes = [str(p) for p in err["loc"] if p not in ("body", "query", "path")]
            campos.append({"field": ".".join(partes) or "cuerpo", "issue": err["msg"]})
        return _respuesta(peticion, validacion(campos))

    @app.exception_handler(StarletteHTTPException)
    async def _http(peticion: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Incluye los 404 de rutas inexistentes y los 405. Sin este manejador
        # saldrían con la forma {"detail": "..."} de Starlette, que el frontend
        # no sabe leer.
        codigos = {
            400: "VALIDATION_ERROR",
            401: "UNAUTHENTICATED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            413: "PAYLOAD_TOO_LARGE",
            415: "UNSUPPORTED_MEDIA_TYPE",
            429: "RATE_LIMITED",
        }
        codigo = codigos.get(exc.status_code, "INTERNAL_ERROR")
        return _respuesta(
            peticion, ErrorApi(codigo, str(exc.detail), exc.status_code)
        )

    @app.exception_handler(Exception)
    async def _no_controlado(peticion: Request, exc: Exception) -> JSONResponse:
        id_peticion = _id_peticion(peticion)
        # La traza va al registro del servidor, no a la respuesta.
        registro.exception("Error no controlado [%s]", id_peticion)
        return _respuesta(
            peticion,
            ErrorApi(
                "INTERNAL_ERROR",
                "Ocurrió un error inesperado. Si persiste, informe el identificador de la petición.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
        )
