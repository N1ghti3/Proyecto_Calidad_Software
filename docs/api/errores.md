# Errores de la API

## Estructura única

Toda respuesta con estado ≥ 400 usa esta forma, sin excepciones:

```json
{
  "error": {
    "code": "CODIGO_ESTABLE",
    "message": "Texto legible en español",
    "details": {},
    "requestId": "req_01HX8Z5K"
  }
}
```

**Regla obligatoria para el frontend:** la lógica se decide **solo** con `error.code` y el estado HTTP. `error.message` es para mostrar o registrar, puede cambiar de redacción en cualquier versión y no debe compararse nunca.

**Regla obligatoria para el backend:** los mensajes no revelan detalles internos (consultas, trazas, nombres de archivo, versiones). Todo error 500 se registra con su `requestId` y se responde genérico.

## Catálogo de códigos

| Código | HTTP | Descripción | Cuándo ocurre | Qué debe hacer el frontend |
| --- | --- | --- | --- | --- |
| `VALIDATION_ERROR` | 400 | La petición no cumple el esquema | Campo faltante, tipo incorrecto, valor fuera de rango, campo desconocido, filtro u orden no admitido | Marcar los campos indicados en `details.fields`; no reintentar sin corregir |
| `CONSENT_REQUIRED` | 400 | Falta la autorización de tratamiento de datos (RN-16) | `dataProcessingConsent` ausente o `false` al crear la orden | Resaltar la casilla de autorización con el motivo; no enviar de nuevo hasta que se marque |
| `INVALID_CREDENTIALS` | 401 | Usuario o contraseña incorrectos | Inicio de sesión fallido | Mensaje genérico de credenciales inválidas; nunca indicar si el correo existe |
| `UNAUTHENTICATED` | 401 | Falta el token o está vencido | Petición a `/admin` sin `Authorization` válido | Limpiar la sesión y llevar al inicio de sesión conservando el destino |
| `FORBIDDEN` | 403 | Autenticado pero sin permiso | Reservado para el futuro esquema de roles | Mostrar mensaje de acceso denegado; no reintentar |
| `NOT_FOUND` | 404 | El recurso no existe o no es visible | Producto despublicado, identificador inexistente, orden que no coincide con el correo (RN-18) | Pantalla de «no encontrado»; no revelar que el recurso pueda existir |
| `INVALID_STATE_TRANSITION` | 409 | La transición de estado no está permitida (RN-13) | Pasar de `ENTREGADA` a `PREPARADA`, cancelar una orden entregada | Recargar la orden y mostrar su estado real |
| `INSUFFICIENT_STOCK` | 409 | No hay unidades suficientes (RN-07, RN-11) | Validación de carrito o creación de orden con existencias insuficientes | Mostrar, línea por línea, las unidades disponibles de `details.items` y permitir ajustar el carrito |
| `CONFLICT` | 409 | Conflicto de unicidad | `sku`, `slug`, talla repetida dentro del producto o correo de administrador duplicado | Señalar el campo en conflicto de `details.field` |
| `PAYLOAD_TOO_LARGE` | 413 | Archivo o cuerpo demasiado grande | Imagen mayor al límite en la carga | Indicar el tamaño máximo de `details.maxBytes` |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | Tipo de archivo o `Content-Type` no admitido | Carga de un archivo que no es imagen admitida | Indicar los formatos admitidos de `details.allowed` |
| `RATE_LIMITED` | 429 | Demasiadas peticiones | Protección de inicio de sesión y de creación de órdenes | Esperar los segundos de `details.retryAfterSeconds` y reintentar una sola vez |
| `INTERNAL_ERROR` | 500 | Error no controlado | Fallo del servidor | Mensaje genérico con el `requestId` visible; ofrecer reintentar |
| `SERVICE_UNAVAILABLE` | 503 | Dependencia no disponible | Base de datos inaccesible o mantenimiento | Mensaje de servicio temporalmente no disponible; reintento con espera |

> No existe un código para fallos de notificación: por RN-15 un error de correo **no** es un error de la petición. La orden se confirma y la notificación queda en estado `FALLIDA`, visible en el panel (EP-20).

## Contenido de `details` por código

| Código | Forma de `details` | Ejemplo |
| --- | --- | --- |
| `VALIDATION_ERROR` | `{ "fields": [ { "field": "customer.email", "issue": "formato inválido" } ] }` | Campo a campo, con ruta en notación de punto |
| `CONSENT_REQUIRED` | `{ "field": "dataProcessingConsent" }` | — |
| `INSUFFICIENT_STOCK` | `{ "items": [ { "variantId": "…", "productName": "…", "size": "M", "requestedQuantity": 2, "availableUnits": 0 } ] }` | Solo las líneas problemáticas |
| `INVALID_STATE_TRANSITION` | `{ "currentStatus": "ENTREGADA", "requestedStatus": "PREPARADA", "allowed": [] }` | — |
| `CONFLICT` | `{ "field": "sku", "value": "CAM-OVR-NEG-M" }` | — |
| `PAYLOAD_TOO_LARGE` | `{ "maxBytes": 5242880 }` | — |
| `UNSUPPORTED_MEDIA_TYPE` | `{ "allowed": ["image/jpeg", "image/png", "image/webp"] }` | — |
| `RATE_LIMITED` | `{ "retryAfterSeconds": 60 }` | — |
| Resto | `{}` | Objeto vacío, nunca `null` |

## Ejemplos completos

Validación (400):

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "La solicitud contiene campos inválidos",
    "details": {
      "fields": [
        { "field": "customer.phone", "issue": "debe tener entre 7 y 15 dígitos" },
        { "field": "items[0].quantity", "issue": "debe ser mayor o igual a 1" }
      ]
    },
    "requestId": "req_01HX8Z5K"
  }
}
```

Existencias insuficientes (409) — respuesta de RN-11:

```json
{
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "Algunos productos ya no tienen unidades suficientes",
    "details": {
      "items": [
        {
          "variantId": "9a4c0f2e-1f4b-4a8e-9f1e-2c7d6b5a4321",
          "productName": "Camiseta oversize negra",
          "size": "M",
          "requestedQuantity": 1,
          "availableUnits": 0
        }
      ]
    },
    "requestId": "req_01HX8Z7M"
  }
}
```

Este es el error que reciben las **40 solicitudes rechazadas** del escenario de RNF-02.

## Reglas de diseño de errores

1. **Códigos estables.** Un código publicado no se renombra; si cambia el significado, se crea otro y el anterior se marca obsoleto en el registro de cambios de [README.md](README.md).
2. **Un error por causa raíz.** La respuesta no mezcla validación de formato con reglas de negocio: primero se valida el formato (400) y solo después se evalúa el negocio (409).
3. **Sin información sensible.** Nunca se revela si un correo está registrado, si una orden existe para otro comprador ni detalles de la base de datos.
4. **`requestId` siempre presente**, también en 500, para correlacionar con los registros del servidor.
5. **Errores de negocio previsibles ≠ 500.** Un `INSUFFICIENT_STOCK` es un resultado esperado del sistema, no un fallo: se responde 409 y no se registra como incidente.

## Mapa error → requisito → prueba

| Código | Requisito | Regla | Prueba |
| --- | --- | --- | --- |
| `INSUFFICIENT_STOCK` | REQ-02, REQ-03, RNF-02 | RN-07, RN-11 | CP-10, CP-23, CP-90 |
| `CONSENT_REQUIRED` | REQ-08 | RN-16 | CP-70, CP-73 |
| `INVALID_STATE_TRANSITION` | REQ-07 | RN-13 | CP-61 |
| `UNAUTHENTICATED` | REQ-06, RNF-04 | RN-19 | CP-51 |
| `INVALID_CREDENTIALS` | RNF-04 | RN-20 | CP-82 |
| `NOT_FOUND` | REQ-01, REQ-03 | RN-01, RN-18 | CP-03, CP-22 |
| `VALIDATION_ERROR` | Todos | RN-29 | CP-25 |
| `UNSUPPORTED_MEDIA_TYPE`, `PAYLOAD_TOO_LARGE` | REQ-06, RNF-01 | RN-22 | CP-54 |
