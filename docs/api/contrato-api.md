# Contrato API

Reglas generales de la interfaz entre C1 (frontend) y C3 (API). El detalle por endpoint está en [endpoints.md](endpoints.md); los objetos, en [modelos.md](modelos.md).

## Reglas de transporte

| Aspecto | Regla |
| --- | --- |
| Protocolo | HTTPS en el ambiente desplegado (RNF-04). En desarrollo local se admite HTTP contra `localhost` |
| Formato | JSON UTF-8 en peticiones y respuestas; `multipart/form-data` solo en EP-16 |
| Base | `/api/v1` — el prefijo de versión es obligatorio en toda ruta |
| Métodos | `GET` (consulta), `POST` (creación o acción compleja sin estado), `PATCH` (modificación parcial). No se usa `PUT` ni `DELETE` en este alcance: no existe reemplazo total ni borrado físico (RN-23, RN-25) |
| Códigos | 200 consulta correcta · 201 creación · 400 formato o consentimiento · 401 autenticación · 403 permiso · 404 inexistente · 409 conflicto de negocio · 413/415 archivo · 429 límite · 500/503 servidor |
| Idempotencia | `GET` y `PATCH` son idempotentes. `POST /orders` acepta `Idempotency-Key` para tolerar reintentos del comprador (`DECISIÓN PROPUESTA`) |
| Zona horaria | Todo `datetime` en UTC; la conversión a hora de Bogotá es del frontend |

## Autenticación y sesión

| Aspecto | Regla |
| --- | --- |
| Mecanismo | Token de portador (`Authorization: Bearer <token>`) obtenido en EP-10. `DECISIÓN PROPUESTA` — el PDF exige autenticación del administrador pero no fija el mecanismo (ADR-001) |
| Alcance | Solo administradores. El comprador nunca se autentica |
| Vigencia | 8 horas (`expiresIn`). Al vencer, la API responde `UNAUTHENTICATED` y el frontend vuelve al inicio de sesión conservando el destino |
| Renovación | No hay refresco automático en este alcance: añadiría estado de sesión sin requisito que lo respalde |
| Almacenamiento en el cliente | En memoria de la aplicación durante la sesión; no se escribe en almacenamiento persistente del navegador |
| Registro | El inicio de sesión actualiza `last_login_at`; los intentos fallidos se limitan por frecuencia (`RATE_LIMITED`) |

## Límites de la API

| Límite | Valor | Motivo |
| --- | --- | --- |
| `pageSize` máximo | 50 | Proteger RNF-01 y la instancia de capa gratuita |
| Líneas por carrito u orden | 50 | Evitar peticiones abusivas |
| Unidades por línea | 20 | Coherente con la operación de un micronegocio |
| Tamaño de imagen | 5 MB por archivo | Coherente con RNF-01 y con la capacidad de la instancia |
| Intentos de inicio de sesión | 5 por minuto y por cuenta | OWASP A07 |
| Creación de órdenes | 10 por minuto y por IP | Evitar abuso sin bloquear la prueba de concurrencia (que usa un margen mayor en el ambiente de pruebas) |

Todos los límites son `DECISIÓN PROPUESTA`: el PDF no los fija, pero sin ellos el contrato quedaría abierto y el frontend no podría anticipar los rechazos.

## Compatibilidad y versiones

| Cambio | ¿Compatible? | Procedimiento |
| --- | --- | --- |
| Agregar un campo opcional a una petición | Sí | Actualizar `modelos.md` y avisar en el registro de cambios |
| Agregar un campo a una respuesta | Sí | El frontend ignora lo que no conoce |
| Agregar un valor a una enumeración | Sí | El frontend debe tolerar valores desconocidos (convenciones) |
| Renombrar o eliminar un campo | **No** | Nueva versión de ruta (`/api/v2`) o cambio coordinado; ver ADR-004 |
| Cambiar el tipo de un campo | **No** | Igual que el anterior |
| Cambiar el significado de un código de error | **No** | Se crea un código nuevo |

## Flujo completo de compra

Corresponde al flujo principal del PDF (apartado 9.1). Cada paso indica pantalla, endpoint y errores posibles.

| Paso | Pantalla frontend | Endpoint | Request | Backend | Response | Errores |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Catálogo | Listado | `GET /products` + `GET /categories` | Filtros `q`, `category`, `size`, `page` | Consulta productos publicados y calcula disponibilidad (RN-01, RN-02) | `Page<ProductSummaryResponse>`, `array<CategoryResponse>` | `VALIDATION_ERROR` |
| 2. Detalle del producto | Detalle | `GET /products/{slug}` | `slug` | Devuelve producto con variantes y existencias | `ProductResponse` | `NOT_FOUND` |
| 3. Selección de variante | Detalle | — | — | — (selección local) | — | — |
| 4. Carrito | Carrito | `POST /cart/validate` | `items[]` | Comprueba existencias sin reservar (RN-06, RN-07) | `CartValidationResponse` | `VALIDATION_ERROR`, `NOT_FOUND` |
| 5. Validación de disponibilidad previa | Carrito → Checkout | `POST /cart/validate` | Carrito completo | Revalida todas las líneas (REQ-02.5) | `CartValidationResponse` con `valid` | `VALIDATION_ERROR`, `NOT_FOUND` |
| 6. Datos y autorización | Checkout | — | Formulario con `dataProcessingConsent` | Validación en cliente **no vinculante** | — | — |
| 7. Creación de orden y descuento transaccional | Checkout | `POST /orders` | `CreateOrderRequest` | Transacción: bloquea, verifica, descuenta, crea orden y audita (RN-08 … RN-11, RN-24) | `201 OrderResponse` | `CONSENT_REQUIRED`, `INSUFFICIENT_STOCK`, `VALIDATION_ERROR`, `NOT_FOUND`, `RATE_LIMITED`, `INTERNAL_ERROR` |
| 8. Checkout simulado | Confirmación | — (misma respuesta) | — | `simulatedCheckout = true` (RN-12) | — | — |
| 9. Confirmación | Confirmación | — | — | — | Muestra `orderNumber`, líneas y total | — |
| 10. Notificación | — (fuera de pantalla) | — | — | Notificación asíncrona al comprador y al administrador (RN-14); si falla, queda `FALLIDA` (RN-15) | — | No afecta la respuesta |
| 11. Consulta posterior | Consulta de orden | `GET /orders/{orderNumber}?email=` | Número + correo | Verifica coincidencia (RN-18) | `OrderResponse` enmascarado | `NOT_FOUND`, `VALIDATION_ERROR` |

### Flujo de administración

| Paso | Pantalla | Endpoint | Regla |
| --- | --- | --- | --- |
| Iniciar sesión | Login | `POST /auth/login` | RN-19, RN-20 |
| Cargar producto | Formulario único | `POST /admin/products` + `POST /admin/products/{id}/images` | RN-21, RN-22 |
| Publicar | Lista de productos | `PATCH /admin/products/{id}/publish` | RN-01, RN-21 |
| Ajustar existencias | Inventario | `PATCH /admin/variants/{id}/inventory` | RN-09, RN-24 |
| Preparar y entregar | Órdenes | `PATCH /admin/orders/{id}/status` | RN-13, RN-27 |
| Revisar evidencia | Auditoría | `GET /admin/audit-logs` | RN-25 |
| Revisar notificaciones fallidas | Notificaciones | `GET /admin/notifications` | RN-15 |

## Comportamiento bajo concurrencia (lo que el frontend debe asumir)

1. Una validación de carrito exitosa **no garantiza** que la orden se confirme: entre ambas llamadas otro comprador puede agotar la variante (RN-06).
2. Un `409 INSUFFICIENT_STOCK` en `POST /orders` es un resultado normal, no un fallo del sistema: la interfaz debe explicarlo sin lenguaje de error técnico y ofrecer ajustar el carrito.
3. Tras un 409, el frontend debe refrescar la disponibilidad con `POST /cart/validate` antes de reintentar.
4. Nunca se debe reintentar automáticamente un `POST /orders` que devolvió 409: el resultado sería el mismo.
5. En el escenario de RNF-02 (50 solicitudes, 10 unidades), 10 clientes reciben 201 y 40 reciben 409; ambas respuestas son correctas.

## Contrato de errores

Estructura única, códigos estables y reglas de uso: [errores.md](errores.md). El frontend nunca decide con `message`.

## Verificación del contrato

| Qué se verifica | Cómo | Documento |
| --- | --- | --- |
| Que la API responde lo que el contrato dice | Pruebas de API por endpoint | `../pruebas/pruebas-api.md` |
| Que las reglas de negocio se cumplen | Pruebas unitarias y de integración | `../pruebas/estrategia-pruebas.md` |
| Que el inventario permanece consistente | Prueba de concurrencia CP-90 | `../pruebas/pruebas-concurrencia.md` |
| Que el frontend cubre todos los estados | Revisión cruzada contra `frontend-backend-contract.md` | `frontend-backend-contract.md` |
