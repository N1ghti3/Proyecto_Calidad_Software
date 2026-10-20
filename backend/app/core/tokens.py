"""Emisión y verificación del token del panel (RN-19, ADR-006).

Alcance deliberadamente estrecho: hay un solo tipo de usuario con acceso al
panel, no hay roles y no hay token de refresco. El token lleva el identificador
del administrador, su correo y una expiración; nada más. Cada campo adicional
sería información que viaja en claro —un JWT va firmado, no cifrado— sin que
nadie la necesite.

La duración es de ocho horas: cubre una jornada del micronegocio sin obligar a
volver a entrar, y vence el mismo día si alguien deja la sesión abierta en un
equipo compartido.

`JWT_SECRET` no tiene valor por omisión a propósito. Un secreto por omisión es
un secreto conocido, y la aplicación prefiere no arrancar a arrancar insegura.
"""

from __future__ import annotations

import datetime
import uuid

import jwt

from app.core.config import obtener_settings

ALGORITMO = "HS256"
DURACION_HORAS = 8


class TokenInvalido(Exception):
    """Token ausente, mal formado, con firma incorrecta o vencido.

    Se trata igual en todos los casos: distinguirlos le diría a quien prueba
    tokens cuál de sus intentos estuvo más cerca.
    """


def _secreto() -> str:
    secreto = obtener_settings().jwt_secret
    if not secreto or len(secreto) < 16:
        raise RuntimeError(
            "JWT_SECRET ausente o demasiado corto. Defínalo en .env con una "
            "cadena larga y aleatoria; sin él la autenticación del panel no es segura."
        )
    return secreto


def emitir(admin_id: uuid.UUID, correo: str) -> tuple[str, int]:
    """Devuelve el token y los segundos que faltan para que venza."""
    ahora = datetime.datetime.now(datetime.timezone.utc)
    vence = ahora + datetime.timedelta(hours=DURACION_HORAS)
    cuerpo = {
        "sub": str(admin_id),
        "email": correo,
        "iat": int(ahora.timestamp()),
        "exp": int(vence.timestamp()),
    }
    return jwt.encode(cuerpo, _secreto(), algorithm=ALGORITMO), DURACION_HORAS * 3600


def verificar(token: str) -> uuid.UUID:
    """Devuelve el identificador del administrador o levanta TokenInvalido."""
    try:
        cuerpo = jwt.decode(token, _secreto(), algorithms=[ALGORITMO])
        return uuid.UUID(cuerpo["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise TokenInvalido from exc
