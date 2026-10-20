"""Acceso al panel: EP-10 y EP-11.

Dos cuidados que no se ven en la forma del endpoint:

**El error no distingue causas.** Correo inexistente y contraseña incorrecta
devuelven el mismo INVALID_CREDENTIALS. Distinguirlos convierte el inicio de
sesión en un oráculo que confirma qué correos están registrados (OWASP A07).

**Se verifica el hash aunque el correo no exista.** Si la ruta devolviera de
inmediato al no encontrar el usuario, la respuesta sería medible más rápida y
el tiempo revelaría lo que el mensaje calla. Verificar contra un hash de
descarte iguala los tiempos.
"""

from __future__ import annotations

import datetime

from fastapi import APIRouter
from sqlalchemy import select

from app.api import errores
from app.api.deps import Administrador, SesionDb
from app.core import tokens
from app.core.seguridad import hashear_contrasena, verificar_contrasena
from app.models.administracion import AdminUser
from app.schemas.ordenes import AdminUserResponse, LoginRequest, LoginResponse

router = APIRouter(tags=["autenticación"])

# Hash de descarte, calculado una vez al importar el módulo. Sirve para gastar
# el mismo tiempo cuando el correo no existe.
_HASH_SENUELO = hashear_contrasena("contrasena-que-nadie-usa-jamas")


@router.post("/auth/login", response_model=LoginResponse)
def iniciar_sesion(peticion: LoginRequest, sesion: SesionDb):
    """EP-10. Autentica al administrador y entrega el token."""
    correo = peticion.email.strip().lower()
    admin = sesion.scalar(select(AdminUser).where(AdminUser.email == correo))

    if admin is None:
        verificar_contrasena(peticion.password, _HASH_SENUELO)
        raise errores.credenciales_invalidas()

    if not admin.active or not verificar_contrasena(peticion.password, admin.password_hash):
        raise errores.credenciales_invalidas()

    admin.last_login_at = datetime.datetime.now(datetime.timezone.utc)
    sesion.commit()

    token, segundos = tokens.emitir(admin.id, admin.email)
    return LoginResponse(access_token=token, expires_in=segundos)


@router.get("/auth/me", response_model=AdminUserResponse)
def sesion_actual(admin: Administrador):
    """EP-11. El frontend la usa al cargar para saber si la sesión sigue viva."""
    return AdminUserResponse(id=admin.id, email=admin.email, full_name=admin.full_name)
