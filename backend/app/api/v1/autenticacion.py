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

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.api import errores
from app.api.deps import Administrador, SesionDb
from app.core import tokens
from app.core.config import obtener_settings
from app.core.limite import LimiteIntentos
from app.core.seguridad import hashear_contrasena, verificar_contrasena
from app.models.administracion import AdminUser
from app.schemas.ordenes import AdminUserResponse, LoginRequest, LoginResponse

router = APIRouter(tags=["autenticación"])

# Hash de descarte, calculado una vez al importar el módulo. Sirve para gastar
# el mismo tiempo cuando el correo no existe.
_HASH_SENUELO = hashear_contrasena("contrasena-que-nadie-usa-jamas")

_ajustes = obtener_settings()
_por_cuenta = LimiteIntentos(_ajustes.login_intentos_por_cuenta, _ajustes.login_ventana_segundos)
_por_ip = LimiteIntentos(_ajustes.login_intentos_por_ip, _ajustes.login_ventana_segundos)


@router.post("/auth/login", response_model=LoginResponse)
def iniciar_sesion(peticion: LoginRequest, sesion: SesionDb, solicitud: Request):
    """EP-10. Autentica al administrador y entrega el token.

    El límite se comprueba antes de verificar la contraseña: de lo contrario
    el bloqueo solo frenaría la respuesta, no el ataque, porque cada intento
    seguiría comparando contra el hash real.
    """
    correo = peticion.email.strip().lower()
    ip = solicitud.client.host if solicitud.client else "desconocida"
    espera = max(_por_cuenta.espera(correo), _por_ip.espera(ip))
    if espera:
        raise errores.limite_excedido(espera)

    admin = sesion.scalar(select(AdminUser).where(AdminUser.email == correo))

    if admin is None:
        verificar_contrasena(peticion.password, _HASH_SENUELO)
        _por_cuenta.fallo(correo)
        _por_ip.fallo(ip)
        raise errores.credenciales_invalidas()

    if not admin.active or not verificar_contrasena(peticion.password, admin.password_hash):
        _por_cuenta.fallo(correo)
        _por_ip.fallo(ip)
        raise errores.credenciales_invalidas()

    _por_cuenta.limpiar(correo)
    admin.last_login_at = datetime.datetime.now(datetime.timezone.utc)
    sesion.commit()

    token, segundos = tokens.emitir(admin.id, admin.email)
    return LoginResponse(
        access_token=token,
        expires_in=segundos,
        user=AdminUserResponse(id=admin.id, email=admin.email, full_name=admin.full_name),
    )


@router.get("/auth/me", response_model=AdminUserResponse)
def sesion_actual(admin: Administrador):
    """EP-11. El frontend la usa al cargar para saber si la sesión sigue viva."""
    return AdminUserResponse(id=admin.id, email=admin.email, full_name=admin.full_name)
