"""Configuración leída del entorno.

Ninguna credencial vive en el código ni en un archivo versionado: todo sale del
archivo `.env` de la raíz del repositorio, creado a partir de `.env.example` y
excluido por `.gitignore` (riesgo R-07, RNF-04).

ADR-010 establece dos roles de base de datos con privilegios distintos, y por
eso hay dos cadenas de conexión:

- ``database_url``            → rol ``tiendalocal_app``, con el que corre la
                                aplicación. No puede actualizar ni borrar
                                ``audit_log``.
- ``database_migration_url``  → rol ``tiendalocal_owner``, con el que corre
                                Alembic. Crea tablas y extensiones.

Que la aplicación arranque con el rol propietario anularía la protección de la
auditoría sin aviso, de modo que son dos campos separados y ninguno tiene valor
por omisión.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> backend/app/core -> backend/app -> backend -> raíz
RAIZ_REPOSITORIO = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Variables de entorno del backend."""

    model_config = SettingsConfigDict(
        env_file=RAIZ_REPOSITORIO / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Conexión de la aplicación en ejecución (rol tiendalocal_app).
    database_url: str

    # Conexión de las migraciones (rol tiendalocal_owner).
    database_migration_url: str

    # Contraseña del rol de la aplicación. La migración inicial la necesita
    # para crear ese rol; después de eso, nada más la usa.
    app_db_password: str

    # Secreto de firma del token del panel (RN-19, ADR-006). Cadena vacía por
    # omisión para que las herramientas que solo tocan la base —Alembic, la
    # siembra— no exijan definirlo; la API sí lo valida antes de emitir el
    # primer token, en app/core/tokens.py. Un valor por omisión real sería un
    # secreto conocido, que es peor que no tener ninguno.
    jwt_secret: str = ""

    # Orígenes autorizados para CORS, separados por coma. En desarrollo el
    # frontend corre en otro puerto que la API, de modo que sin esto el
    # navegador bloquea toda petición antes de que salga.
    cors_origenes: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Límite de intentos fallidos de inicio de sesión (contrato-api.md, OWASP
    # A07): 5 por minuto y por cuenta. El de dirección IP es más holgado para
    # no castigar a una oficina que comparte salida a internet.
    login_intentos_por_cuenta: int = 5
    login_intentos_por_ip: int = 20
    login_ventana_segundos: int = 60

    # Carpeta donde se guardan las imágenes que se cargan desde el panel
    # (EP-16). Fuera de frontend/public a propósito: esas fotos nacen en
    # ejecución, no al construir, y nginx sirve public/ desde la imagen del
    # contenedor. Vacía equivale a la omisión: sin ese cuidado, MEDIA_DIR=
    # en el .env resolvía a «.» y las imágenes caían en la carpeta de trabajo.
    media_dir: str = ""

    # RN-22: límites de la carga. 5 MiB es lo que errores.md declara como
    # ejemplo de `maxBytes`; 1200 px cubre el detalle a doble densidad.
    imagen_max_bytes: int = 5 * 1024 * 1024
    imagen_ancho_max: int = 1200

    @property
    def carpeta_media(self) -> Path:
        return Path(self.media_dir) if self.media_dir.strip() else RAIZ_REPOSITORIO / "media"


@lru_cache
def obtener_settings() -> Settings:
    """Devuelve la configuración, leída una sola vez por proceso."""
    return Settings()  # type: ignore[call-arg]
