"""RN-20 — las contraseñas se almacenan con función de derivación de clave.

Verifica `backend/app/core/seguridad.py`. Relacionado con CP-82 (RNF-04).
"""

from __future__ import annotations

import pytest
from argon2 import PasswordHasher

from app.core.seguridad import (
    LONGITUD_MINIMA,
    hashear_contrasena,
    necesita_recalculo,
    verificar_contrasena,
)

CONTRASENA = "una-contrasena-larga"


def test_el_hash_es_argon2id_y_no_contiene_la_contrasena():
    resultado = hashear_contrasena(CONTRASENA)

    assert resultado.startswith("$argon2id$")
    assert CONTRASENA not in resultado


def test_la_misma_contrasena_produce_hashes_distintos():
    # La sal es aleatoria: dos administradores con la misma contraseña no
    # comparten el valor almacenado.
    assert hashear_contrasena(CONTRASENA) != hashear_contrasena(CONTRASENA)


def test_verifica_la_contrasena_correcta():
    assert verificar_contrasena(CONTRASENA, hashear_contrasena(CONTRASENA)) is True


def test_rechaza_la_contrasena_incorrecta():
    assert verificar_contrasena("otra-contrasena-larga", hashear_contrasena(CONTRASENA)) is False


@pytest.mark.parametrize(
    "hash_almacenado",
    ["", "texto-cualquiera", "$argon2id$v=19$m=65536,t=3,p=4$corrupto", "$2b$12$hash-de-bcrypt"],
)
def test_un_hash_ilegible_devuelve_false_sin_lanzar(hash_almacenado):
    # Quien llama no debe poder distinguir «contraseña incorrecta» de «hash
    # ilegible»: esa diferencia le diría algo a un atacante.
    assert verificar_contrasena(CONTRASENA, hash_almacenado) is False


@pytest.mark.parametrize("corta", ["", "a" * (LONGITUD_MINIMA - 1)])
def test_rechaza_contrasenas_cortas(corta):
    with pytest.raises(ValueError):
        hashear_contrasena(corta)


def test_acepta_exactamente_la_longitud_minima():
    assert hashear_contrasena("a" * LONGITUD_MINIMA).startswith("$argon2id$")


def test_un_hash_actual_no_necesita_recalculo():
    assert necesita_recalculo(hashear_contrasena(CONTRASENA)) is False


def test_un_hash_con_parametros_debiles_necesita_recalculo():
    debil = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(CONTRASENA)
    assert necesita_recalculo(debil) is True


def test_un_hash_ilegible_necesita_recalculo():
    assert necesita_recalculo("texto-cualquiera") is True
