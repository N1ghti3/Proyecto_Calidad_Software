# Casos de prueba

Catálogo de casos referenciados desde requisitos, criterios de aceptación, reglas de negocio y endpoints. Formato: precondición → acción → resultado esperado.

Convención de numeración: CP-0x catálogo · CP-1x carrito · CP-2x órdenes · CP-3x checkout · CP-4x notificaciones · CP-5x administración · CP-6x estados de orden · CP-7x datos personales · CP-8x no funcionales · CP-90 concurrencia.

---

## Catálogo (REQ-01)

| ID | Nivel | Precondición | Acción | Resultado esperado | Criterio |
| --- | --- | --- | --- | --- | --- |
| CP-01 | API | Catálogo con productos disponibles y agotados | `GET /products` | 200; cada elemento trae `availableUnits` e `inStock` coherentes con el inventario | CA-01-0 |
| CP-02 | API | Productos en varias categorías y tallas | `GET /products?category=camisetas&size=M` | 200; solo productos de esa categoría que tienen talla M | CA-01-0, CA-01-5 |
| CP-03 | API | Un producto publicado y otro despublicado | `GET /products` y `GET /products/{slug-despublicado}` | El despublicado no aparece en el listado; su detalle responde 404 `NOT_FOUND` | CA-01-1 |
| CP-04 | API | Producto «Camiseta oversize negra» | `GET /products?q=CAMISETA` y `q=camiséta` | 200; el producto aparece en ambos casos | CA-01-2 |
| CP-05 | API | Producto con tallas S (2), M (0), L (5) | `GET /products/{slug}` | 200; `variants[]` con `availableUnits` 2, 0 y 5 e `inStock` correspondiente | CA-01-3 |
| CP-06 | API + E2E | Producto publicado con todas las variantes en 0 | `GET /products` y vista de listado | Aparece con `inStock: false`; la interfaz lo marca como agotado y no permite comprar | CA-01-4 |

## Carrito (REQ-02)

| ID | Nivel | Precondición | Acción | Resultado esperado | Criterio |
| --- | --- | --- | --- | --- | --- |
| CP-10 | API | Variante con 0 unidades | `POST /cart/validate` con `quantity: 1` | 200 con `items[0].available: false` y `availableUnits: 0`; la interfaz impide agregar e informa el motivo | CA-02-0 |
| CP-11 | API | Variante con 3 unidades | `POST /cart/validate` con `quantity: 5` | 200 con `available: false` y `availableUnits: 3` | CA-02-1 |
| CP-12 | E2E | Carrito con dos líneas | Recargar la página | El carrito conserva su contenido (sesión) | CA-02-2 |
| CP-13 | Integration | Carrito válido; otro comprador agota la variante | Revalidar el carrito | La línea pasa a `available: false`; la interfaz bloquea continuar hasta corregir | CA-02-3 |

## Órdenes e inventario (REQ-03)

| ID | Nivel | Precondición | Acción | Resultado esperado | Criterio |
| --- | --- | --- | --- | --- | --- |
| CP-20 | Integration | Variante con 5 unidades | `POST /orders` con `quantity: 2` | 201; orden `CONFIRMADA`; existencias quedan en 3 | CA-03-0 |
| CP-21 | Integration | Fallo forzado después de descontar (simulación de error) | `POST /orders` | La transacción se revierte: no hay orden y las existencias no cambian | CA-03-0 |
| CP-22 | API | Orden creada | `GET /orders/{orderNumber}?email=` correcto e incorrecto | 200 con la orden íntegra (precio congelado) en el primer caso; 404 en el segundo | CA-03-1, RN-18, RN-28 |
| CP-23 | Integration | Línea A disponible, línea B agotada | `POST /orders` con ambas | 409 `INSUFFICIENT_STOCK`; `details.items` incluye solo B; existencias de A sin cambios; no se crea orden | CA-03-2 |
| CP-24 | Integration | Orden confirmada | `GET /admin/audit-logs?entityType=INVENTORY` | Existe un registro por variante con `source: ORDEN`, `oldValue`, `newValue` y fecha | CA-03-3 |
| CP-25 | API | — | `POST /orders` con `items: []` y con `quantity: 0` | 400 `VALIDATION_ERROR` en ambos casos | RN-29 |

## Checkout simulado (REQ-04)

| ID | Nivel | Precondición | Acción | Resultado esperado | Criterio |
| --- | --- | --- | --- | --- | --- |
| CP-30 | E2E | Carrito válido | Completar el checkout | La interfaz muestra el aviso de simulación antes y después de confirmar; la orden queda `CONFIRMADA` con `simulatedCheckout: true` | CA-04-0 |
| CP-31 | API + revisión | — | Inspeccionar esquema de `POST /orders` y el formulario | No existe ningún campo de tarjeta ni de medio de pago | CA-04-1 |

## Notificaciones (REQ-05)

| ID | Nivel | Precondición | Acción | Resultado esperado | Criterio |
| --- | --- | --- | --- | --- | --- |
| CP-40 | Integration | Servicio de correo disponible (doble de prueba) | Confirmar una orden | Se generan dos notificaciones (comprador y administrador) con identificador, productos y cantidades, entregadas en < 5 min | CA-05-0 |
| CP-41 | Integration | Servicio de correo que responde error o cuota agotada | Confirmar una orden | La orden permanece `CONFIRMADA` (201); la notificación queda `FALLIDA` con `lastError` y es visible en `GET /admin/notifications` | CA-05-1 |

## Administración (REQ-06)

| ID | Nivel | Precondición | Acción | Resultado esperado | Criterio |
| --- | --- | --- | --- | --- | --- |
| CP-50 | Integration | Variante con 10 unidades; administrador autenticado | `PATCH /admin/variants/{id}/inventory` con `stockQuantity: 12`, `reason` | 200; existencias 12; registro de auditoría con usuario, `oldValue: "10"`, `newValue: "12"`, motivo y fecha | CA-06-0 |
| CP-51 | API | Sin token o con token vencido | Llamar a cada endpoint `/admin` | 401 `UNAUTHENTICATED` en todos; ningún dato modificado | CA-06-1 |
| CP-52 | Integration | Producto publicado con una orden previa | `PATCH /admin/products/{id}/publish` con `false` | 200; desaparece del catálogo público; sigue en `/admin/products` y en la orden previa | CA-06-2 |
| CP-53 | API | Variante con existencias | `PATCH .../inventory` con `stockQuantity: -1` | 400 `VALIDATION_ERROR`; existencias sin cambio | CA-06-3 |
| CP-54 | Integration | Administrador autenticado | `POST /admin/products/{id}/images` con imagen grande, con archivo no imagen y sin `alt` | Imagen válida: 201 con versión optimizada y dimensiones; archivo grande: 413; tipo no admitido: 415; sin `alt`: 400 | CA-06-4 |
| CP-55 | API | Producto sin variantes activas | `PATCH /admin/products/{id}/publish` con `true` | 400 `VALIDATION_ERROR`; el producto no se publica | RN-21 |

## Estados de orden (REQ-07)

| ID | Nivel | Precondición | Acción | Resultado esperado | Criterio |
| --- | --- | --- | --- | --- | --- |
| CP-60 | Integration | Orden `CONFIRMADA` | `PATCH /admin/orders/{id}/status` a `PREPARADA` | 200; estado persistido; registro de auditoría con `STATUS_CHANGE` | CA-07-0 |
| CP-61 | API | Orden `ENTREGADA` | Cambiar a `PREPARADA` | 409 `INVALID_STATE_TRANSITION` con `currentStatus` y `allowed` | CA-07-1 |
| CP-62 | Integration | Orden `CONFIRMADA` de 2 unidades; existencias 3 | Cancelar con motivo | 200; estado `CANCELADA`; existencias vuelven a 5; auditoría con `source: CANCELACION` | CA-07-2 |

## Datos personales (REQ-08)

| ID | Nivel | Precondición | Acción | Resultado esperado | Criterio |
| --- | --- | --- | --- | --- | --- |
| CP-70 | E2E | Formulario de pedido completo | Enviar sin marcar la autorización | No se envía la orden; se indica el motivo junto a la casilla | CA-08-0 |
| CP-71 | E2E + A11y | Formulario de pedido | Inspeccionar | El aviso de privacidad y la política son accesibles desde el formulario, alcanzables por teclado | CA-08-1 |
| CP-72 | Integration | Orden creada con autorización | Consultar el registro | Constan `dataProcessingConsent`, `privacyNoticeVersion` y `consentAt` | CA-08-2 |
| CP-73 | API | — | `POST /orders` sin `dataProcessingConsent` (directo a la API) | 400 `CONSENT_REQUIRED`; no se crea la orden ni se descuenta inventario | CA-08-3 |

## No funcionales

| ID | Nivel | Precondición | Acción | Resultado esperado | Criterio |
| --- | --- | --- | --- | --- | --- |
| CP-80 | Performance | Catálogo con doce productos con imagen | Auditoría de rendimiento móvil, tres ejecuciones | Promedio: peso transferido ≤ 1,5 MB y contenido principal < 3 s | CA-RNF-01 |
| CP-81 | Accessibility | Pantallas del flujo principal | Auditoría automatizada + revisión manual de contraste, texto alternativo, teclado y etiquetado | Cero incumplimientos de nivel A y AA en esas cuatro pautas | CA-RNF-03 |
| CP-82 | Security | Ambiente desplegado y esquema de datos | Revisión de configuración, esquema y respuestas | Todo el tráfico sobre TLS; ninguna contraseña en texto claro; ningún campo personal sin finalidad declarada; consultas parametrizadas; sin secretos en el repositorio | CA-RNF-04 |
| CP-83 | Usabilidad | Cinco participantes del perfil de propietario | Tarea: alta de un producto con imagen y existencias | Al menos cuatro completan sin ayuda en < 5 min | CA-RNF-05 |
| CP-84 | CI/CD | Canal automatizado configurado | Ejecutar construcción y despliegue | Imagen de aplicación < 250 MB; despliegue sin pasos manuales; el flujo falla si falla una prueba | CA-RNF-06 |
| **CP-90** | **Concurrency** | **Un producto con una variante y 10 unidades** | **50 solicitudes simultáneas de 1 unidad** | **10 órdenes confirmadas (201), 40 rechazadas con `INSUFFICIENT_STOCK` (409), existencia final 0, sin inventario negativo** | **CA-RNF-02** |

CP-90 se detalla en [pruebas-concurrencia.md](pruebas-concurrencia.md).

---

## Cobertura por requisito

| Requisito | Casos | ¿Cubierto? |
| --- | --- | --- |
| REQ-01 | CP-01 … CP-06 | Sí |
| REQ-02 | CP-10 … CP-13 | Sí |
| REQ-03 | CP-20 … CP-25, CP-90 | Sí |
| REQ-04 | CP-30, CP-31 | Sí |
| REQ-05 | CP-40, CP-41 | Sí |
| REQ-06 | CP-50 … CP-55 | Sí |
| REQ-07 | CP-60 … CP-62 | Sí |
| REQ-08 | CP-70 … CP-73 | Sí |
| RNF-01 | CP-80 | Sí |
| RNF-02 | CP-90 | Sí |
| RNF-03 | CP-81 | Sí |
| RNF-04 | CP-82, CP-51 | Sí |
| RNF-05 | CP-83 | Sí |
| RNF-06 | CP-84 | Sí |
