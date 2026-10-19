# Historias de usuario

Derivadas exclusivamente del PDF (actores de la Tabla 1, flujo del apartado 9.1 y requisitos del apartado 10). **No se agregan funcionalidades comunes de e-commerce que el documento no respalde** (cuentas de comprador, listas de deseos, cupones, valoraciones, devoluciones, envíos, pagos).

Actores (PDF, Tabla 1 y apartado 9.3):

| Actor | Descripción |
| --- | --- |
| Comprador | Usuario externo del catálogo; accede de forma anónima, sin cuenta. |
| Administrador | Propietario del micronegocio; se autentica para operar el panel. |
| Personal de apoyo | Usuario operativo de lectura de pedidos; origen de REQ-07. En el sistema opera con el mismo acceso administrativo (ver nota al final). |

Prioridad: se hereda del requisito de origen (PDF, Tabla 10 y apartado 12.3).

---

## HU-01 — Ver el catálogo

| Campo | Valor |
| --- | --- |
| **ID** | HU-01 |
| **Actor** | Comprador |
| **Historia** | **Como** comprador **quiero** ver el listado de productos publicados con su precio y disponibilidad **para** saber qué puedo comprar sin escribirle al vendedor. |
| **Prioridad** | Alta |
| **Criterios de aceptación** | CA-01-1, CA-01-4 |
| **Requisitos** | REQ-01 (REQ-01.1, REQ-01.5, REQ-01.6) |
| **Reglas de negocio** | RN-01, RN-02, RN-03 |
| **Endpoints** | EP-01 |

## HU-02 — Buscar un producto por nombre

| Campo | Valor |
| --- | --- |
| **ID** | HU-02 |
| **Actor** | Comprador |
| **Historia** | **Como** comprador **quiero** buscar un producto por su nombre **para** encontrarlo sin recorrer todo el catálogo. |
| **Prioridad** | Alta |
| **Criterios de aceptación** | CA-01-2 |
| **Requisitos** | REQ-01 (REQ-01.3) |
| **Reglas de negocio** | RN-01, RN-02 |
| **Endpoints** | EP-01 |

## HU-03 — Filtrar por categoría y talla

| Campo | Valor |
| --- | --- |
| **ID** | HU-03 |
| **Actor** | Comprador |
| **Historia** | **Como** comprador **quiero** filtrar el catálogo por categoría y por talla **para** ver solo los productos que me sirven. |
| **Prioridad** | Alta |
| **Criterios de aceptación** | CA-01-0, CA-01-5 |
| **Requisitos** | REQ-01 (REQ-01.4) |
| **Reglas de negocio** | RN-01, RN-02, RN-04 |
| **Endpoints** | EP-01, EP-02 |

## HU-04 — Consultar el detalle y la disponibilidad por talla

| Campo | Valor |
| --- | --- |
| **ID** | HU-04 |
| **Actor** | Comprador |
| **Historia** | **Como** comprador **quiero** abrir el detalle de un producto y ver la disponibilidad de cada talla **para** decidir la compra sin esperar respuesta humana. |
| **Prioridad** | Alta |
| **Criterios de aceptación** | CA-01-3 |
| **Requisitos** | REQ-01 (REQ-01.2) |
| **Reglas de negocio** | RN-02, RN-03, RN-04 |
| **Endpoints** | EP-03 |

## HU-05 — Agregar al carrito con comprobación de existencias

| Campo | Valor |
| --- | --- |
| **ID** | HU-05 |
| **Actor** | Comprador |
| **Historia** | **Como** comprador **quiero** agregar una talla de un producto a mi carrito y que el sistema compruebe que hay unidades **para** no avanzar con algo que no existe. |
| **Prioridad** | Alta |
| **Criterios de aceptación** | CA-02-0, CA-02-1, CA-02-2 |
| **Requisitos** | REQ-02 (REQ-02.1, REQ-02.2, REQ-02.3) |
| **Reglas de negocio** | RN-05, RN-06, RN-07 |
| **Endpoints** | EP-04 |

## HU-06 — Revalidar el carrito antes de confirmar

| Campo | Valor |
| --- | --- |
| **ID** | HU-06 |
| **Actor** | Comprador |
| **Historia** | **Como** comprador **quiero** que el sistema revise mi carrito completo justo antes de confirmar **para** enterarme de un agotamiento antes de llenar mis datos. |
| **Prioridad** | Alta |
| **Criterios de aceptación** | CA-02-3 |
| **Requisitos** | REQ-02 (REQ-02.4, REQ-02.5) `DECISIÓN PROPUESTA` |
| **Reglas de negocio** | RN-06, RN-07 |
| **Endpoints** | EP-04 |

## HU-07 — Confirmar el pedido con descuento de inventario

| Campo | Valor |
| --- | --- |
| **ID** | HU-07 |
| **Actor** | Comprador |
| **Historia** | **Como** comprador **quiero** confirmar mi pedido y recibir un número de orden **para** tener certeza de que las unidades quedaron reservadas para mí. |
| **Prioridad** | Alta |
| **Criterios de aceptación** | CA-03-0, CA-03-1, CA-03-2, CA-03-3, CA-RNF-02 |
| **Requisitos** | REQ-03, RNF-02 |
| **Reglas de negocio** | RN-08, RN-09, RN-10, RN-11 |
| **Endpoints** | EP-05 |

## HU-08 — Completar el checkout simulado

| Campo | Valor |
| --- | --- |
| **ID** | HU-08 |
| **Actor** | Comprador |
| **Historia** | **Como** comprador **quiero** ver de forma explícita que el pago es una simulación académica **para** no creer que realicé una transacción real. |
| **Prioridad** | Alta |
| **Criterios de aceptación** | CA-04-0, CA-04-1 |
| **Requisitos** | REQ-04 |
| **Reglas de negocio** | RN-12 |
| **Endpoints** | EP-05, EP-06 |

## HU-09 — Autorizar el tratamiento de mis datos

| Campo | Valor |
| --- | --- |
| **ID** | HU-09 |
| **Actor** | Comprador |
| **Historia** | **Como** comprador **quiero** autorizar expresamente el tratamiento de mis datos y poder leer el aviso de privacidad **para** saber qué datos entrego y con qué finalidad. |
| **Prioridad** | Alta |
| **Criterios de aceptación** | CA-08-0, CA-08-1, CA-08-2, CA-08-3 |
| **Requisitos** | REQ-08, RNF-04 |
| **Reglas de negocio** | RN-16, RN-17 |
| **Endpoints** | EP-05 |

## HU-10 — Recibir la confirmación del pedido

| Campo | Valor |
| --- | --- |
| **ID** | HU-10 |
| **Actor** | Comprador |
| **Historia** | **Como** comprador **quiero** recibir una notificación con el detalle de mi pedido **para** conservar el soporte de lo que compré. |
| **Prioridad** | Media |
| **Criterios de aceptación** | CA-05-0 |
| **Requisitos** | REQ-05 |
| **Reglas de negocio** | RN-14, RN-15 |
| **Endpoints** | EP-05 (efecto), EP-06 (consulta) |

## HU-11 — Consultar mi orden después de confirmarla

| Campo | Valor |
| --- | --- |
| **ID** | HU-11 |
| **Actor** | Comprador |
| **Historia** | **Como** comprador **quiero** volver a consultar mi orden con su número **para** revisar su contenido y su estado. |
| **Prioridad** | Media |
| **Criterios de aceptación** | CA-03-1 |
| **Requisitos** | REQ-03 (REQ-03.3); Ley 527 de 1999 (PDF 3.3): la orden debe conservarse íntegra y recuperable |
| **Reglas de negocio** | RN-18 |
| **Endpoints** | EP-06 |

---

## HU-12 — Autenticarse en el panel

| Campo | Valor |
| --- | --- |
| **ID** | HU-12 |
| **Actor** | Administrador |
| **Historia** | **Como** administrador **quiero** autenticarme **para** operar el catálogo y las órdenes de mi negocio. |
| **Prioridad** | Alta |
| **Criterios de aceptación** | CA-06-1, CA-RNF-04 |
| **Requisitos** | REQ-06, RNF-04 |
| **Reglas de negocio** | RN-19, RN-20 |
| **Endpoints** | EP-10, EP-11 |

## HU-13 — Dar de alta un producto en un solo formulario

| Campo | Valor |
| --- | --- |
| **ID** | HU-13 |
| **Actor** | Administrador |
| **Historia** | **Como** propietario sin formación técnica **quiero** cargar un producto con su imagen, sus tallas y sus existencias en un único formulario **para** publicarlo sin ayuda. |
| **Prioridad** | Alta |
| **Criterios de aceptación** | CA-06-4, CA-RNF-05 |
| **Requisitos** | REQ-06 (REQ-06.1, REQ-06.4, REQ-06.5), RNF-05 |
| **Reglas de negocio** | RN-21, RN-22 |
| **Endpoints** | EP-12, EP-14, EP-16 |

## HU-14 — Publicar y despublicar productos

| Campo | Valor |
| --- | --- |
| **ID** | HU-14 |
| **Actor** | Administrador |
| **Historia** | **Como** administrador **quiero** publicar o despublicar un producto **para** controlar qué se ofrece sin borrar su historial. |
| **Prioridad** | Alta |
| **Criterios de aceptación** | CA-06-2 |
| **Requisitos** | REQ-06 (REQ-06.1, REQ-06.7) |
| **Reglas de negocio** | RN-03, RN-23 |
| **Endpoints** | EP-13 |

## HU-15 — Ajustar existencias con auditoría

| Campo | Valor |
| --- | --- |
| **ID** | HU-15 |
| **Actor** | Administrador |
| **Historia** | **Como** administrador **quiero** ajustar las existencias de una talla y que quede registrado quién lo hizo y con qué valores **para** poder reconstruir cualquier variación. |
| **Prioridad** | Alta |
| **Criterios de aceptación** | CA-06-0, CA-06-3 |
| **Requisitos** | REQ-06 (REQ-06.2, REQ-06.3, REQ-06.6) |
| **Reglas de negocio** | RN-09, RN-24, RN-25 |
| **Endpoints** | EP-15 |

## HU-16 — Ver las órdenes recibidas

| Campo | Valor |
| --- | --- |
| **ID** | HU-16 |
| **Actor** | Administrador / Personal de apoyo |
| **Historia** | **Como** responsable de empaque y despacho **quiero** una lista de pedidos confirmados con su contenido y dirección **para** prepararlos sin pedir información por otro canal. |
| **Prioridad** | Media |
| **Criterios de aceptación** | CA-07-0 |
| **Requisitos** | REQ-07 (REQ-07.1) |
| **Reglas de negocio** | RN-26 |
| **Endpoints** | EP-17 |

## HU-17 — Cambiar el estado de una orden

| Campo | Valor |
| --- | --- |
| **ID** | HU-17 |
| **Actor** | Administrador / Personal de apoyo |
| **Historia** | **Como** responsable de empaque y despacho **quiero** marcar una orden como preparada o entregada **para** saber qué falta por despachar. |
| **Prioridad** | Media |
| **Criterios de aceptación** | CA-07-0, CA-07-1 |
| **Requisitos** | REQ-07 (REQ-07.2, REQ-07.3) |
| **Reglas de negocio** | RN-13, RN-26, RN-27 |
| **Endpoints** | EP-18 |

## HU-18 — Cancelar una orden y devolver las unidades

| Campo | Valor |
| --- | --- |
| **ID** | HU-18 |
| **Actor** | Administrador |
| **Historia** | **Como** administrador **quiero** cancelar una orden y que sus unidades vuelvan al inventario **para** que el stock siga reflejando la realidad. |
| **Prioridad** | Media — `DECISIÓN PROPUESTA` (el PDF no describe cancelación; ver REQ-07.4) |
| **Criterios de aceptación** | CA-07-2 |
| **Requisitos** | REQ-07 (REQ-07.4) |
| **Reglas de negocio** | RN-13, RN-27 |
| **Endpoints** | EP-18 |

## HU-19 — Consultar la auditoría de inventario y órdenes

| Campo | Valor |
| --- | --- |
| **ID** | HU-19 |
| **Actor** | Administrador |
| **Historia** | **Como** administrador **quiero** consultar el registro de cambios de inventario y de estados de órdenes **para** reconstruir qué pasó y cuándo. |
| **Prioridad** | Media |
| **Criterios de aceptación** | CA-03-3, CA-06-0, CA-07-0 |
| **Requisitos** | REQ-06 (REQ-06.3), REQ-07 (REQ-07.3); componente C6 del PDF |
| **Reglas de negocio** | RN-24, RN-25, RN-27 |
| **Endpoints** | EP-19 |

## HU-20 — Ver el estado de las notificaciones

| Campo | Valor |
| --- | --- |
| **ID** | HU-20 |
| **Actor** | Administrador |
| **Historia** | **Como** administrador **quiero** ver en el panel las notificaciones que no pudieron enviarse **para** contactar al comprador por otro medio. |
| **Prioridad** | Media |
| **Criterios de aceptación** | CA-05-1 |
| **Requisitos** | REQ-05 (REQ-05.3, REQ-05.4); riesgo R-08 del PDF |
| **Reglas de negocio** | RN-15 |
| **Endpoints** | EP-17, EP-20 |

---

## Notas de derivación

1. **No existe historia de registro o inicio de sesión del comprador.** El PDF establece que el comprador accede de forma anónima al catálogo (apartado 9.3) y el proyecto no incluye cuentas de comprador.
2. **El personal de apoyo no tiene un rol técnico propio.** `DECISIÓN PROPUESTA`: opera con el mismo usuario administrador. El PDF lo identifica como actor con necesidad de lectura de pedidos, pero no define un segundo rol ni permisos diferenciados; crear un sistema de roles completo excedería el alcance de dieciséis semanas (R-05). Si el propietario lo solicita, se registra como candidato a trabajo futuro (riesgo R-04, congelación de alcance al cierre de I-2).
3. **HU-18 y HU-06 no provienen literalmente del PDF**; se derivan de la necesidad de mantener la consistencia del inventario y están marcadas como decisión propuesta en el requisito correspondiente.
