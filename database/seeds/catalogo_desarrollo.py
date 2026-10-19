"""Catálogo de demostración: los datos, separados del guion que los inserta.

**Datos anonimizados.** Ningún nombre de negocio, persona o dirección real
(riesgo R-02, contingencia del supuesto S-01, y compromiso ético del apartado
12.4 del PDF). Los productos son verosímiles para un micronegocio bogotano de
moda urbana y artesanías, y ninguno existe.

Estos datos **no son el punto de partida de las pruebas automatizadas.** La
estrategia de pruebas lo fija: «cada prueba de integración crea y limpia sus
propios datos; ninguna depende del orden de ejecución», y CP-90 dice que su
estado inicial lo crea la propia prueba. Sembrar aquí lo que una prueba necesita
crearía justo la dependencia que esa regla prohíbe.

Para qué sirven entonces:

| Uso | Qué exige del catálogo |
| --- | --- |
| Desarrollar y ver la aplicación | Un catálogo que no parezca vacío |
| CP-80, rendimiento (RNF-01) | **Doce productos publicados, cada uno con imagen** |
| CP-81, accesibilidad (RNF-03) | Texto alternativo real en cada imagen, no de relleno |
| CP-83, usabilidad (RNF-05) | Un catálogo poblado donde dar de alta un producto más |
| Demostración al propietario | Estados interesantes: agotados, sin publicar |

Estados que el catálogo cubre a propósito:

- un producto con una talla agotada y otras disponibles;
- un producto publicado con **todas** sus tallas en cero;
- una artesanía de pieza única agotada;
- un producto **sin publicar** que sí tiene variantes activas;
- un producto sin publicar y **sin variantes activas**, que RN-21 impide publicar.

Las rutas de imagen apuntan a `/media/productos/…`, que es lo que servirán C2 y
C5. **Los archivos no existen todavía**, de modo que la interfaz mostrará el
texto alternativo en su lugar — lo que, de paso, deja ver si ese texto está bien
escrito.
"""

from __future__ import annotations

# Sufijo del SKU para cada talla.
#
# El SKU es un código interno y la restricción `ck_product_variant_sku_formato`
# exige `[A-Z0-9-]+`: solo ASCII en mayúsculas. «ÚNICA» no sirve como sufijo
# porque lleva tilde, así que se traduce. Esto es un detalle de la construcción
# del código, no del catálogo de tallas: la talla sigue llamándose «ÚNICA» en la
# API y en la interfaz.
SUFIJO_SKU_POR_TALLA: dict[str, str] = {
    "XS": "XS",
    "S": "S",
    "M": "M",
    "L": "L",
    "XL": "XL",
    "XXL": "XXL",
    "ÚNICA": "UNI",
}

# (nombre, slug)
CATEGORIAS: tuple[tuple[str, str], ...] = (
    ("Camisetas", "camisetas"),
    ("Ropa exterior", "ropa-exterior"),
    ("Artesanías", "artesanias"),
    ("Accesorios", "accesorios"),
)

# Cada producto:
#   categoria     slug de su categoría
#   name, slug    el slug es la ruta pública del detalle; solo [a-z0-9-]
#   price_cop     pesos colombianos enteros
#   published     False en los dos últimos, a propósito
#   variantes     (talla, unidades, activa)
#   imagenes      (archivo, texto alternativo, ancho, alto)
#
# Las tallas deben existir en size_catalog, que siembra la migración inicial:
# XS, S, M, L, XL, XXL y ÚNICA (ADR-008).
PRODUCTOS: tuple[dict, ...] = (
    # ---------------------------------------------------------------- Camisetas
    {
        "categoria": "camisetas",
        "name": "Camiseta oversize negra",
        "slug": "camiseta-oversize-negra",
        "description": (
            "Camiseta de corte holgado en algodón peinado de 180 gramos, con "
            "hombros caídos y cuello reforzado. Teñida en negro profundo con "
            "proceso de bajo consumo de agua. Confeccionada en Bogotá."
        ),
        "price_cop": 89000,
        "published": True,
        "sku": "TL-CAM-001",
        "variantes": (("S", 2, True), ("M", 0, True), ("L", 5, True)),
        "imagenes": (
            (
                "camiseta-oversize-negra-frente.webp",
                "Camiseta negra de corte holgado vista de frente sobre fondo gris claro",
                1200,
                1200,
            ),
            (
                "camiseta-oversize-negra-espalda.webp",
                "Espalda de la camiseta negra, sin estampado, con etiqueta tejida en el cuello",
                1200,
                1200,
            ),
        ),
        "nota": "Talla M agotada y otras disponibles: el caso mixto del listado.",
    },
    {
        "categoria": "camisetas",
        "name": "Camiseta básica blanca",
        "slug": "camiseta-basica-blanca",
        "description": (
            "Camiseta de corte recto en algodón de 160 gramos, cuello redondo "
            "con ribete elástico. Prelavada para que no ceda con el uso."
        ),
        "price_cop": 65000,
        "published": True,
        "sku": "TL-CAM-002",
        "variantes": (("M", 3, True), ("L", 7, True), ("XL", 11, True)),
        "imagenes": (
            (
                "camiseta-basica-blanca-frente.webp",
                "Camiseta blanca de cuello redondo colgada de un gancho de madera",
                1200,
                1200,
            ),
        ),
    },
    {
        "categoria": "camisetas",
        "name": "Camiseta estampada Ñandú",
        "slug": "camiseta-estampada-nandu",
        "description": (
            "Estampado serigrafiado a mano de un ñandú sobre algodón crudo. "
            "Cada pieza tiene variaciones mínimas de registro, porque el "
            "estampado no es industrial."
        ),
        "price_cop": 95000,
        "published": True,
        "sku": "TL-CAM-003",
        "variantes": (("S", 4, True), ("M", 0, True), ("L", 9, True)),
        "imagenes": (
            (
                "camiseta-estampada-nandu-frente.webp",
                "Camiseta color crudo con la silueta de un ñandú serigrafiada en tinta negra sobre el pecho",
                1200,
                1200,
            ),
        ),
        "nota": (
            "El nombre lleva Ñ y tilde a propósito: al buscar «nandu» o «ÑANDÚ» "
            "debe aparecer igual (CA-01-2)."
        ),
    },
    {
        "categoria": "camisetas",
        "name": "Camiseta tie dye edición limitada",
        "slug": "camiseta-tie-dye-edicion-limitada",
        "description": (
            "Teñida por anudado en lotes de veinte piezas, sin dos iguales. "
            "Algodón de 180 gramos. Edición cerrada: no se reabastece."
        ),
        "price_cop": 110000,
        "published": True,
        "sku": "TL-CAM-004",
        "variantes": (("S", 0, True), ("M", 0, True), ("L", 0, True)),
        "imagenes": (
            (
                "camiseta-tie-dye-frente.webp",
                "Camiseta teñida por anudado en espiral con tonos azul y violeta, extendida sobre una mesa",
                1200,
                1200,
            ),
        ),
        "nota": (
            "Publicada y con TODAS las tallas en cero: debe aparecer en el "
            "listado marcada como agotada, sin permitir compra."
        ),
    },
    # ------------------------------------------------------------ Ropa exterior
    {
        "categoria": "ropa-exterior",
        "name": "Chaqueta bomber reversible",
        "slug": "chaqueta-bomber-reversible",
        "description": (
            "Chaqueta de dos caras: nailon en una, algodón acolchado en la "
            "otra. Puños y cintura con elástico tejido. Bolsillos internos en "
            "ambos lados."
        ),
        "price_cop": 219000,
        "published": True,
        "sku": "TL-EXT-001",
        "variantes": (("S", 4, True), ("M", 2, True), ("L", 0, True)),
        "imagenes": (
            (
                "chaqueta-bomber-cara-nailon.webp",
                "Chaqueta bomber verde oliva en nailon, vista de frente con el cierre subido a la mitad",
                1200,
                1500,
            ),
            (
                "chaqueta-bomber-cara-algodon.webp",
                "La misma chaqueta volteada, mostrando la cara de algodón acolchado color arena",
                1200,
                1500,
            ),
        ),
    },
    {
        "categoria": "ropa-exterior",
        "name": "Buzo cuello tortuga",
        "slug": "buzo-cuello-tortuga",
        "description": (
            "Buzo de punto grueso con cuello alto doblado, en mezcla de algodón "
            "y lana. Tejido en telar circular, sin costuras laterales."
        ),
        "price_cop": 132000,
        "published": True,
        "sku": "TL-EXT-002",
        "variantes": (("M", 10, True), ("L", 6, True), ("XL", 1, True)),
        "imagenes": (
            (
                "buzo-cuello-tortuga-frente.webp",
                "Buzo de punto color mostaza con cuello alto doblado, visto de frente",
                1200,
                1500,
            ),
        ),
    },
    {
        "categoria": "ropa-exterior",
        "name": "Sudadera con capucha grafiti",
        "slug": "sudadera-con-capucha-grafiti",
        "description": (
            "Sudadera con capucha forrada y bolsillo canguro, con un estampado "
            "inspirado en los murales del centro de Bogotá. Interior "
            "perchado."
        ),
        "price_cop": 149000,
        "published": False,
        "sku": "TL-EXT-003",
        "variantes": (("M", 8, True), ("L", 5, True)),
        "imagenes": (
            (
                "sudadera-capucha-grafiti-frente.webp",
                "Sudadera gris con capucha y un estampado de mural en tonos rojo y azul en el pecho",
                1200,
                1500,
            ),
        ),
        "nota": (
            "SIN PUBLICAR, pero con variantes activas y existencias: no debe "
            "aparecer en el listado público y su detalle debe responder 404."
        ),
    },
    {
        "categoria": "ropa-exterior",
        "name": "Chaleco acolchado reversible",
        "slug": "chaleco-acolchado-reversible",
        "description": (
            "Chaleco acolchado sin mangas, con relleno reciclado. Pendiente de "
            "definir tallas con el taller antes de ofrecerlo."
        ),
        "price_cop": 175000,
        "published": False,
        "sku": "TL-EXT-004",
        "variantes": (("M", 0, False),),
        "imagenes": (
            (
                "chaleco-acolchado-frente.webp",
                "Chaleco acolchado azul marino sin mangas, con cierre frontal, sobre un maniquí",
                1200,
                1500,
            ),
        ),
        "nota": (
            "SIN PUBLICAR y SIN variantes activas: intentar publicarlo debe "
            "fallar con VALIDATION_ERROR (RN-21)."
        ),
    },
    # -------------------------------------------------------------- Artesanías
    {
        "categoria": "artesanias",
        "name": "Mochila wayuu tejida a mano",
        "slug": "mochila-wayuu-tejida-a-mano",
        "description": (
            "Tejida en crochet por artesanas de La Guajira, con gaza trenzada. "
            "Entre veinte y treinta días de trabajo por pieza. Los patrones "
            "son de diseño propio de cada tejedora, por lo que no se repiten."
        ),
        "price_cop": 245000,
        "published": True,
        "sku": "TL-ART-001",
        "variantes": (("ÚNICA", 3, True),),
        "imagenes": (
            (
                "mochila-wayuu-completa.webp",
                "Mochila wayuu tejida en crochet con franjas geométricas en rojo, ocre y azul, con gaza trenzada",
                1200,
                1200,
            ),
            (
                "mochila-wayuu-detalle-gaza.webp",
                "Detalle de la gaza trenzada de la mochila, mostrando el ancho del tejido",
                1200,
                1200,
            ),
        ),
    },
    {
        "categoria": "artesanias",
        "name": "Sombrero vueltiao quince vueltas",
        "slug": "sombrero-vueltiao-quince-vueltas",
        "description": (
            "Trenzado en caña flecha con quince vueltas, lo que lo hace "
            "flexible y de trama cerrada. El número de vueltas indica la "
            "finura del tejido: a más vueltas, más fino y más tiempo de "
            "trabajo."
        ),
        "price_cop": 189000,
        "published": True,
        "sku": "TL-ART-002",
        "variantes": (("ÚNICA", 2, True),),
        "imagenes": (
            (
                "sombrero-vueltiao-superior.webp",
                "Sombrero vueltiao visto desde arriba, con el trenzado en zigzag negro y beige de la copa",
                1200,
                1200,
            ),
        ),
    },
    {
        "categoria": "artesanias",
        "name": "Hamaca de algodón de San Jacinto",
        "slug": "hamaca-de-algodon-de-san-jacinto",
        "description": (
            "Tejida en telar vertical con algodón hilado a mano. Dos metros de "
            "largo por uno con sesenta de ancho, con flecos anudados en los "
            "bordes. Soporta hasta ciento veinte kilogramos."
        ),
        "price_cop": 320000,
        "published": True,
        "sku": "TL-ART-003",
        "variantes": (("ÚNICA", 1, True),),
        "imagenes": (
            (
                "hamaca-san-jacinto-extendida.webp",
                "Hamaca de algodón a rayas en tonos tierra, extendida y colgada entre dos postes de madera",
                1600,
                1000,
            ),
        ),
        "nota": "Una sola unidad: útil para ver el aviso de últimas unidades.",
    },
    {
        "categoria": "artesanias",
        "name": "Jarrón en cerámica de Ráquira",
        "slug": "jarron-en-ceramica-de-raquira",
        "description": (
            "Torneado a mano en barro de Ráquira y cocido en horno de leña, lo "
            "que deja marcas de fuego irrepetibles en la superficie. Sin "
            "esmaltar por dentro: no es apto para contener agua."
        ),
        "price_cop": 78000,
        "published": True,
        "sku": "TL-ART-004",
        "variantes": (("ÚNICA", 0, True),),
        "imagenes": (
            (
                "jarron-raquira-frente.webp",
                "Jarrón de barro cocido color terracota con marcas oscuras de horno de leña, sobre fondo neutro",
                1200,
                1200,
            ),
        ),
        "nota": "Pieza única agotada: publicada pero sin existencias.",
    },
    # -------------------------------------------------------------- Accesorios
    {
        "categoria": "accesorios",
        "name": "Cinturón en cuero repujado",
        "slug": "cinturon-en-cuero-repujado",
        "description": (
            "Cuero curtido al vegetal, repujado a mano con motivos de hoja y "
            "hebilla de latón macizo. Se oscurece con el uso."
        ),
        "price_cop": 72000,
        "published": True,
        "sku": "TL-ACC-001",
        "variantes": (("ÚNICA", 6, True),),
        "imagenes": (
            (
                "cinturon-cuero-repujado-detalle.webp",
                "Detalle del repujado de hojas en un cinturón de cuero café con hebilla de latón",
                1200,
                800,
            ),
        ),
    },
    {
        "categoria": "accesorios",
        "name": "Pulsera en hilo encerado",
        "slug": "pulsera-en-hilo-encerado",
        "description": (
            "Anudada a mano en hilo encerado, con cierre corredizo ajustable. "
            "Resiste el agua y no destiñe."
        ),
        "price_cop": 25000,
        "published": True,
        "sku": "TL-ACC-002",
        "variantes": (("ÚNICA", 15, True),),
        "imagenes": (
            (
                "pulsera-hilo-encerado-conjunto.webp",
                "Tres pulseras de hilo encerado anudado en verde, negro y mostaza, con cierre corredizo",
                1200,
                1200,
            ),
        ),
    },
)

# Usuario del panel. Correo en example.com, que es el dominio reservado para
# ejemplos y no entrega correo a nadie: un correo real aquí sería un dato
# personal en un repositorio.
ADMIN_CORREO = "admin@example.com"
ADMIN_NOMBRE = "Administradora de demostración"
