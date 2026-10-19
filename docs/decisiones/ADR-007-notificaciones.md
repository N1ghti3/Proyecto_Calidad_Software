# ADR-007 — Notificación asíncrona con registro persistente

- **Estado:** **Pendiente** — el diseño está decidido; falta confirmar el proveedor de correo y su cuota gratuita
- **Fecha:** 2026-09-25
- **Decide:** Hedixon Cardozo (backend) y Jhon Ortiz (DevOps)
- **Respaldo en el PDF:** REQ-05 (notificación en menos de cinco minutos), riesgo R-08 («registrar la notificación en el sistema y mostrarla en el panel, degradando la funcionalidad sin bloquear el flujo») y apartado 9.3 (servicio de correo transaccional como sistema externo). La **entidad `notification`** y el envío asíncrono son `DECISIÓN PROPUESTA`.

## Contexto

REQ-05 exige notificar al comprador y al administrador en menos de cinco minutos. El servicio de correo es externo y gratuito, con cuota limitada (riesgo R-08, probabilidad baja e impacto bajo).

El conflicto a resolver: si el envío ocurriera dentro de la transacción de la orden, un fallo o una demora del correo podría revertir una orden ya válida o mantener bloqueadas las filas de inventario durante una llamada de red, contradiciendo RNF-02.

## Alternativas consideradas

1. **Envío síncrono dentro de la transacción.**
2. **Envío síncrono después del `COMMIT`**, sin registro persistente.
3. **Envío asíncrono con registro persistente** (entidad `notification` con estado).
4. **Cola de mensajes dedicada** (por ejemplo, un intermediario externo).

| Criterio | A1 en transacción | A2 tras commit | A3 asíncrono con registro | A4 cola |
| --- | --- | --- | --- | --- |
| Riesgo para RNF-02 | **Alto** | Bajo | Bajo | Bajo |
| Cumple la degradación de R-08 | No | No (no queda rastro) | Sí | Sí |
| Costo e infraestructura (R-03) | Nulo | Nulo | Nulo | Requiere componente adicional |
| Esfuerzo (R-05) | Bajo | Bajo | Medio | Alto |
| Visibilidad para el propietario | Ninguna | Ninguna | Panel de notificaciones | Panel + monitoreo |

## Decisión

Envío **asíncrono, fuera de la transacción**, con registro persistente:

1. Al confirmarse la orden (después del `COMMIT`) se crean dos registros en `notification` con estado `PENDIENTE`: uno para el comprador y otro para el administrador.
2. Un proceso en segundo plano del propio servicio intenta el envío y actualiza el estado a `ENVIADA` o `FALLIDA`, incrementando `attempts` y guardando `last_error`.
3. Reintentos: hasta 3 intentos con espera creciente. Agotados, el registro queda `FALLIDA`.
4. Las notificaciones fallidas son visibles en `GET /api/v1/admin/notifications` (EP-20) para que el propietario contacte al comprador por otro medio.
5. Un fallo de notificación **nunca** cambia el estado de la orden ni la respuesta de `POST /orders` (RN-15).

No se introduce una cola externa: añadiría un componente que el PDF no contempla y que contradice el presupuesto nulo y el plazo.

## Puntos abiertos que mantienen el ADR en estado Pendiente

| # | Pregunta | Fecha límite | Responsable |
| --- | --- | --- | --- |
| 1 | Proveedor de correo transaccional gratuito y su cuota diaria | Antes de I-5 | Jhon |
| 2 | Dirección remitente verificada (el proyecto no dispone de dominio propio; se opera con el nombre DNS del proveedor) | Antes de I-5 | Jhon |
| 3 | Si la cuota resulta insuficiente para la demostración, ¿se acepta mostrar la notificación solo en el panel? Afecta el criterio de REQ-05 | Antes de I-5, a consultar con el docente | Equipo |

## Consecuencias

**Positivas**

- La orden se confirma con independencia del estado del correo: RNF-02 y REQ-03 quedan protegidos.
- La degradación prevista en R-08 queda implementada y es observable.
- El registro persistente permite medir el cumplimiento de los cinco minutos de REQ-05 (CP-40).

**Negativas / riesgos**

- El proceso en segundo plano vive dentro del mismo servicio: si el contenedor se reinicia con envíos pendientes, quedan en `PENDIENTE` hasta el siguiente intento. Aceptable para el volumen previsto.
- El comprador puede ver «orden confirmada» sin haber recibido el correo; por eso la interfaz no afirma que la notificación fue enviada (P-05).

## Verificación

- CP-40: dos notificaciones con contenido completo en menos de cinco minutos.
- CP-41: con el servicio caído, la orden sigue confirmada y la notificación queda `FALLIDA` y visible en el panel.
- EP-20 en las pruebas de API.
