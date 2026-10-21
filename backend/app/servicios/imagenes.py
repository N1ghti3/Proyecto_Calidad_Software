"""Optimización de imágenes de producto (RN-22, componente C5).

Tres decisiones:

**El tipo se decide por el contenido, no por la cabecera.** El
`Content-Type` del formulario lo escribe el cliente y puede decir
`image/png` de un ejecutable. Pillow abre el archivo y reconoce su formato;
solo se aceptan JPEG, PNG y WebP.

**Se guarda una versión nueva, nunca el original.** Se corrige la rotación
que indica la cámara, se reduce a `imagen_ancho_max` y se codifica en WebP.
Así se cumple RNF-01 aunque la administradora suba la foto de 6 MB que salió
del teléfono, y de paso se descartan los metadatos EXIF, que en una foto de
celular suelen incluir la ubicación GPS de quien la tomó.

**Límite de píxeles además del de bytes.** Un PNG de pocos kilobytes puede
declarar 40 000 × 40 000 píxeles y agotar la memoria al decodificarse (una
«bomba de descompresión»). Pillow lo detecta si se le fija un máximo.
"""

from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

FORMATOS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}

# 40 megapíxeles: holgado para cualquier cámara de teléfono, muy por debajo de
# lo que tumbaría al proceso.
Image.MAX_IMAGE_PIXELS = 40_000_000


class ImagenNoAdmitida(Exception):
    """El archivo no es una imagen de un formato admitido."""


@dataclass(frozen=True)
class ImagenGuardada:
    ruta_relativa: str  # relativa a la carpeta de medios, con «/»
    ancho: int
    alto: int


def optimizar_y_guardar(
    contenido: bytes, carpeta_media: Path, product_id: uuid.UUID, ancho_max: int
) -> ImagenGuardada:
    try:
        with Image.open(io.BytesIO(contenido)) as original:
            if original.format not in FORMATOS:
                raise ImagenNoAdmitida(original.format or "desconocido")
            original.load()
            imagen = ImageOps.exif_transpose(original)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as e:
        raise ImagenNoAdmitida(str(e)) from e

    # WebP admite transparencia; se conserva solo si la imagen la usa.
    con_alfa = imagen.mode in ("RGBA", "LA") or (imagen.mode == "P" and "transparency" in imagen.info)
    imagen = imagen.convert("RGBA" if con_alfa else "RGB")
    if imagen.width > ancho_max:
        imagen.thumbnail((ancho_max, ancho_max * 10), Image.Resampling.LANCZOS)

    nombre = f"{uuid.uuid4().hex[:12]}-{imagen.width}.webp"
    relativa = f"cargas/{product_id}/{nombre}"
    destino = carpeta_media / relativa
    destino.parent.mkdir(parents=True, exist_ok=True)
    # Sin `exif=`: el archivo nuevo sale sin metadatos.
    imagen.save(destino, "WEBP", quality=80, method=6)
    return ImagenGuardada(relativa, imagen.width, imagen.height)
