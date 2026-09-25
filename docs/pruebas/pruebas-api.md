# Pruebas de API

Verifican que la implementación cumple el contrato de [`../api/`](../api/README.md). Corresponden a la **campaña 2** del PDF («pruebas de integración sobre la API») y se ejecutan en cada cambio dentro del canal de integración continua.

## Qué verifica una prueba de API aquí

1. **Forma:** los campos, tipos, obligatoriedad y nulabilidad coinciden con [`../api/modelos.md`](../api/modelos.md).
2. **Códigos:** el estado HTTP y el `error.code` coinciden con [`../api/endpoints.md`](../api/endpoints.md) y [`../api/errores.md`](../api/errores.md).
3. **Efecto:** el estado de la base de datos después de la llamada es el esperado (no basta con la respuesta).
4. **Reglas:** la regla de negocio asociada se cumple, incluso si el cliente envía datos maliciosos o incompletos.

Se ejecutan contra **PostgreSQL real** en contenedor, nunca contra una base simulada: la propiedad que el proyecto debe demostrar es transaccional.

## Matriz endpoint × caso mínimo

Cada endpoint necesita, como mínimo, un caso correcto, un caso de validación y —cuando aplique— un caso de autenticación y uno de regla de negocio.

| Endpoint | Correcto | Validación | Autenticación | Regla de negocio |
| --- | --- | --- | --- | --- |
| EP-01 `GET /products` | CP-01 | `sort` inválido → 400 | — | CP-03 (no publicados ocultos) |
| EP-02 `GET /categories` | Lista con `productCount` | — | — | — |
| EP-03 `GET /products/{slug}` | CP-05 | slug inexistente → 404 | — | CP-03 |
| EP-04 `POST /cart/validate` | CP-10, CP-11 | `quantity: 0` → 400; `variantId` repetido → 400 | — | CP-13 (no reserva) |
| EP-05 `POST /orders` | CP-20 | CP-25 | — | CP-23, CP-73, CP-90 |
| EP-06 `GET /orders/{n}` | CP-22 | sin `email` → 400 | — | correo que no coincide → 404 |
| EP-10 `POST /auth/login` | 200 con token | correo mal formado → 400 | credenciales incorrectas → 401 | límite de intentos → 429 |
| EP-11 `GET /auth/me` | 200 | — | sin token → 401 | token vencido → 401 |
| EP-12 `POST /admin/products` | 201 con variantes | precio ≤ 0 → 400 | CP-51 | SKU duplicado → 409 |
| EP-13 `PATCH .../publish` | CP-52 | CP-55 | CP-51 | RN-21, RN-23 |
| EP-14 `POST .../variants` | 201 | talla vacía → 400 | CP-51 | talla repetida → 409 |
| EP-15 `PATCH .../inventory` | CP-50 | CP-53 | CP-51 | auditoría creada (CP-24) |
| EP-16 `POST .../images` | CP-54 | sin `alt` → 400 | CP-51 | 413 y 415 |
| EP-17 `GET /admin/orders` | 200 paginado | `status` inválido → 400 | CP-51 | — |
| EP-18 `PATCH .../status` | CP-60 | cancelar sin motivo → 400 | CP-51 | CP-61, CP-62 |
| EP-19 `GET /admin/audit-logs` | CP-24 | rango de fechas inválido → 400 | CP-51 | solo lectura (RN-25) |
| EP-20 `GET /admin/notifications` | CP-41 | `status` inválido → 400 | CP-51 | — |
| EP-21 `GET /admin/products` | 200 con despublicados | `page: 0` → 400 | CP-51 | — |
| EP-22 `PATCH /admin/products/{id}` | 200 | campo desconocido → 400 | CP-51 | precio cambiado no altera órdenes previas (CP-22) |
| EP-23 `GET /admin/orders/{id}` | 200 sin enmascarar | id inválido → 400 | CP-51 | — |
| EP-24 `GET /admin/inventory` | 200 ordenado por existencias | `lowStockThreshold` negativo → 400 | CP-51 | — |

## Pruebas transversales del contrato

| ID | Verificación | Por qué |
| --- | --- | --- |
| API-T1 | Toda respuesta de error tiene `code`, `message`, `details` y `requestId` | Regla única de errores |
| API-T2 | Ninguna colección devuelve `null`; siempre `[]` | Convenciones |
| API-T3 | Un campo desconocido en el cuerpo produce `VALIDATION_ERROR` | Detecta desalineación de nombres entre frontend y backend |
| API-T4 | Todas las fechas terminan en `Z` y son válidas ISO 8601 | Convenciones |
| API-T5 | Todos los importes son enteros (nunca decimales ni cadenas) | Convenciones de dinero |
| API-T6 | Ninguna respuesta pública incluye datos personales sin enmascarar | RN-18, RNF-04 |
| API-T7 | Ningún mensaje de error revela detalles internos (SQL, rutas, trazas) | RNF-04 |
| API-T8 | Los endpoints `/admin` responden 401 sin token, en todos los métodos | RN-19 |
| API-T9 | `GET` no modifica datos (comprobación de efectos) | Semántica HTTP |
| API-T10 | Las respuestas de listado respetan `pageSize` máximo (50) | Límites del contrato |

## Datos y aislamiento

- Cada prueba crea su propio producto, variante e inventario con valores explícitos y los limpia al terminar.
- Ninguna prueba depende del orden de ejecución ni del estado dejado por otra.
- Los correos usados son de dominio de ejemplo; nunca direcciones reales.
- El servicio de correo se sustituye por un doble de prueba que permite forzar el fallo de CP-41.

## Integración con el canal automatizado

| Momento | Qué se ejecuta | Efecto si falla |
| --- | --- | --- |
| En cada cambio (CI) | Unit + integration + API + CP-90 | Se detiene el despliegue (criterio de OE-3) |
| Al cierre de iteración | E2E, rendimiento, accesibilidad | Se registra el hallazgo y se planifica corrección |
| Antes de etiquetar una versión | Todo lo anterior + revisión de seguridad (CP-82) | No se etiqueta |

## Qué no cubren estas pruebas

Rendimiento (CP-80), accesibilidad (CP-81) y usabilidad (CP-83) tienen sus propias campañas: una API correcta no garantiza una interfaz utilizable ni un catálogo ligero.
