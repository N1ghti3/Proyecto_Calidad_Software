"""Derivación y verificación de contraseñas.

RN-20 prohíbe almacenar la contraseña: en `admin_user.password_hash` va el
resultado de una **función de derivación de clave**, no un resumen simple. Un
resumen como SHA-256 es rápido a propósito, y esa velocidad es precisamente lo
que permite probar millones de contraseñas por segundo contra una base filtrada.
Una función de derivación es lenta y con coste de memoria a propósito.

> **DECISIÓN PROVISIONAL — pendiente de ratificar en ADR-006.**
> Se usa **Argon2id** con los parámetros por omisión de `argon2-cffi`, que
> siguen la recomendación del RFC 9106. ADR-006 («Token de portador para el
> administrador») está marcado *pendiente de validar en I-3* y no nombra función
> de derivación. Se elige Argon2id porque es la primera recomendación actual de
> OWASP, porque `argon2-cffi` tiene ruedas precompiladas para Windows y Linux
> —lo que importa con un equipo en Windows y un despliegue en contenedor— y
> porque el hash lleva sus propios parámetros incrustados, de modo que subirlos
> más adelante no invalida los hashes existentes.
>
> Este módulo existe para que la siembra de desarrollo y el futuro inicio de
> sesión usen **una sola implementación**. Si ADR-006 decide otra función, se
> cambia aquí y se vuelven a sembrar los usuarios de desarrollo; los de un
> ambiente real necesitarían restablecer su contraseña, y eso debe quedar
> registrado en ese ADR.

Longitud mínima: se exige por si acaso, pero la política de contraseñas del
panel es cosa de ADR-006 y no de este módulo.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

LONGITUD_MINIMA = 12

_derivador = PasswordHasher()


def hashear_contrasena(contrasena: str) -> str:
    """Deriva el hash que se almacena en `admin_user.password_hash`.

    Cada llamada produce un resultado distinto para la misma contraseña, porque
    la sal es aleatoria y viaja dentro del hash. Dos administradores con la
    misma contraseña no tendrán el mismo valor almacenado, que es justamente lo
    que se busca.
    """
    if not contrasena or len(contrasena) < LONGITUD_MINIMA:
        raise ValueError(
            f"La contraseña debe tener al menos {LONGITUD_MINIMA} caracteres."
        )
    return _derivador.hash(contrasena)


def verificar_contrasena(contrasena: str, hash_almacenado: str) -> bool:
    """Comprueba una contraseña contra su hash.

    Devuelve `False` ante cualquier fallo —contraseña incorrecta, hash corrupto
    o de un formato desconocido— en lugar de propagar la excepción. Quien llama
    no debe distinguir «contraseña incorrecta» de «hash ilegible»: cualquier
    diferencia observable entre esos dos casos le dice a un atacante algo sobre
    el estado de la cuenta.
    """
    try:
        return _derivador.verify(hash_almacenado, contrasena)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def necesita_recalculo(hash_almacenado: str) -> bool:
    """Indica si el hash se derivó con parámetros más débiles que los actuales.

    Permite subir el coste de la derivación con el tiempo: cuando alguien inicia
    sesión correctamente y esto devuelve `True`, se vuelve a derivar el hash con
    los parámetros vigentes y se guarda. Sin esto, subir los parámetros solo
    protegería a los usuarios creados después del cambio.
    """
    try:
        return _derivador.check_needs_rehash(hash_almacenado)
    except InvalidHashError:
        return True
