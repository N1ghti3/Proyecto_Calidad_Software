"""Límite de frecuencia de intentos fallidos de inicio de sesión.

contrato-api.md fija 5 intentos por minuto y por cuenta (OWASP A07). Se lleva
además un contador por dirección IP: sin él, quien prueba una misma contraseña
contra muchas cuentas nunca tocaría el límite de ninguna.

Solo cuentan los intentos **fallidos**, y un acierto limpia el contador de la
cuenta: a la administradora que se equivoca una vez no se le cobra el error en
el siguiente intento.

La memoria es del proceso. Con un solo proceso de uvicorn —el despliegue
previsto— es suficiente; con varias réplicas cada una llevaría su cuenta y el
límite efectivo se multiplicaría, y habría que mover esto a la base o a Redis.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class LimiteIntentos:
    def __init__(self, maximo: int, ventana: float) -> None:
        self.maximo = maximo
        self.ventana = ventana
        self._marcas: dict[str, deque[float]] = defaultdict(deque)
        self._cerrojo = threading.Lock()

    def _purgar(self, clave: str, ahora: float) -> deque[float]:
        marcas = self._marcas[clave]
        while marcas and ahora - marcas[0] >= self.ventana:
            marcas.popleft()
        return marcas

    def espera(self, clave: str) -> int:
        """Segundos que faltan para poder intentar; 0 si no está bloqueada."""
        with self._cerrojo:
            ahora = time.monotonic()
            marcas = self._purgar(clave, ahora)
            if len(marcas) < self.maximo:
                return 0
            return max(1, int(self.ventana - (ahora - marcas[0])) + 1)

    def fallo(self, clave: str) -> None:
        with self._cerrojo:
            self._purgar(clave, time.monotonic()).append(time.monotonic())

    def limpiar(self, clave: str) -> None:
        with self._cerrojo:
            self._marcas.pop(clave, None)
