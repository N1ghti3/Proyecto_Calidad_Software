"""Dependencias compartidas por las rutas: sesión de base de datos y sesión
del administrador.

`administrador_actual` se declara como dependencia y no como middleware para
que la protección sea visible en la firma de cada ruta. Un middleware que
protege «todo lo que empiece por /admin» funciona hasta que alguien añade una
ruta fuera de ese prefijo; una dependencia explícita no se olvida porque sin
ella la ruta no compila con el tipo que espera.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.api import errores
from app.core import tokens
from app.db.sesion import obtener_sesion
from app.models.administracion import AdminUser

SesionDb = Annotated[Session, Depends(obtener_sesion)]


def administrador_actual(peticion: Request, sesion: SesionDb) -> AdminUser:
    """Resuelve el administrador a partir de `Authorization: Bearer <token>`.

    Todos los fallos —cabecera ausente, esquema incorrecto, firma inválida,
    token vencido, usuario inactivo o borrado— salen como el mismo
    UNAUTHENTICATED. Distinguirlos ayudaría más a quien prueba tokens que a
    quien los usa de buena fe.
    """
    cabecera = peticion.headers.get("Authorization", "")
    esquema, _, token = cabecera.partition(" ")
    if esquema.lower() != "bearer" or not token:
        raise errores.no_autenticado()

    try:
        admin_id = tokens.verificar(token)
    except tokens.TokenInvalido:
        raise errores.no_autenticado() from None

    admin = sesion.get(AdminUser, admin_id)
    if admin is None or not admin.active:
        raise errores.no_autenticado()
    return admin


Administrador = Annotated[AdminUser, Depends(administrador_actual)]
