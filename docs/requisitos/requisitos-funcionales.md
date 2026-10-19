# Requisitos funcionales

**Fuente principal:** `ProyectoTiendaLocalCUN.pdf` — apartado 10, Tabla 10 «Requisitos preliminares y criterios de aceptación».

Los identificadores (`REQ-01` … `REQ-08`), el texto del requisito, el origen, la prioridad y el criterio de aceptación provienen del documento y **no se modifican**. Todo lo que el equipo añade para poder implementar (desglose, dependencias, precisiones) se marca como `DECISIÓN PROPUESTA`.

> El PDF declara que la lista «es preliminar y contiene solo requisitos de alto valor; el detalle completo corresponde al Ajuste avanzado de proyecto». Esta especificación es ese detalle: **no agrega requisitos nuevos**, descompone los existentes.

## Prioridad y negociabilidad (PDF, apartado 12.3)

| Grupo | Requisitos | Regla |
| --- | --- | --- |
| Núcleo no negociable | REQ-01, REQ-02, REQ-03, REQ-04, REQ-06, REQ-08, RNF-02 | No pueden diferirse |
| Candidatos a diferirse si una iteración se retrasa | REQ-05, REQ-07, RNF-03 | Prioridad media |

---

## REQ-01 — Catálogo con listado, detalle, búsqueda y filtros

| Campo | Valor |
| --- | --- |
| **ID** | REQ-01 |
| **Tipo** | Funcional |
| **Nombre** | Catálogo público de productos |
| **Descripción** | El sistema deberá presentar un catálogo con listado, detalle, búsqueda por nombre y filtro por categoría y talla, mostrando el estado de disponibilidad de cada producto. |
| **Origen** | Comprador / causa C-02 (catálogo disperso sin estructura ni control de vigencia) |
| **Prioridad** | Alta |
| **Criterio de aceptación** | Dado un catálogo con productos disponibles y agotados, cuando el comprador aplica un filtro, entonces se muestran solo los productos que cumplen el criterio y cada uno indica su disponibilidad actual. |
| **Dependencias** | Modelo de producto, variante y categoría (`docs/arquitectura/modelo-er.md`); estado de publicación gestionado en REQ-06. |

Desglose verificable:

| Sub-ID | Descripción | Origen |
| --- | --- | --- |
| REQ-01.1 | Listado paginado de productos publicados con imagen, nombre, precio y disponibilidad. | PDF Tabla 7 «Catálogo público con listado…» |
| REQ-01.2 | Detalle de producto con descripción, imágenes, categoría y variantes (talla) con su disponibilidad. | PDF Tabla 7 y Tabla 8 (C-02) |
| REQ-01.3 | Búsqueda por nombre. | PDF REQ-01 |
| REQ-01.4 | Filtro por categoría y por talla, combinables. | PDF REQ-01 |
| REQ-01.5 | Los productos no publicados no aparecen en el catálogo público. | PDF Tabla 8 «estado de publicación» + REQ-06 (despublicar) |
| REQ-01.6 | `DECISIÓN PROPUESTA` Los productos agotados se muestran marcados como agotados en lugar de ocultarse, salvo que estén despublicados. | El criterio de aceptación de REQ-01 exige un catálogo «con productos disponibles y agotados»; ocultarlos impediría verificarlo. |

---

## REQ-02 — Carrito con comprobación de existencias

| Campo | Valor |
| --- | --- |
| **ID** | REQ-02 |
| **Tipo** | Funcional |
| **Nombre** | Carrito de compra con validación de disponibilidad |
| **Descripción** | El sistema deberá permitir agregar productos a un carrito y comprobar la existencia disponible en el momento de agregarlos. |
| **Origen** | Comprador / OE-3 |
| **Prioridad** | Alta |
| **Criterio de aceptación** | Dado un producto con cero unidades, cuando el comprador intenta agregarlo, entonces el sistema lo impide y muestra el motivo. |
| **Dependencias** | REQ-01 (selección de producto y variante). Es el «primer punto de control de consistencia» (PDF, Tabla 7); no sustituye a REQ-03. |

Desglose verificable:

| Sub-ID | Descripción | Origen |
| --- | --- | --- |
| REQ-02.1 | El carrito persiste en la sesión del comprador. | PDF Tabla 7 «Carrito de compra con persistencia en sesión» |
| REQ-02.2 | Al agregar una unidad se comprueba la existencia disponible contra el servidor. | PDF REQ-02 |
| REQ-02.3 | Si la variante tiene cero unidades, el sistema impide agregarla e informa el motivo. | Criterio de aceptación REQ-02 |
| REQ-02.4 | `DECISIÓN PROPUESTA` La comprobación del carrito **no reserva** unidades: es informativa y no vinculante. La garantía la da REQ-03. | PDF apartado 9.3: «ninguna comprobación de existencias hecha en el navegador es vinculante». El PDF no define reservas ni su expiración. |
| REQ-02.5 | `DECISIÓN PROPUESTA` Antes de confirmar, el frontend revalida el carrito completo contra el servidor. | Evita llegar al checkout con un carrito obsoleto; sin esto el rechazo de REQ-03 sería la primera señal para el comprador. |

---

## REQ-03 — Orden con descuento transaccional de existencias

| Campo | Valor |
| --- | --- |
| **ID** | REQ-03 |
| **Tipo** | Funcional |
| **Nombre** | Generación de orden con validación transaccional de inventario |
| **Descripción** | El sistema deberá generar una orden con identificador único descontando las existencias dentro de una única transacción. |
| **Origen** | Causa C-01 (ausencia de una única fuente de verdad del inventario) / Objetivo general |
| **Prioridad** | Alta |
| **Criterio de aceptación** | Dado un carrito válido, cuando el comprador confirma, entonces se crea la orden y las existencias se reducen en la misma cantidad; si algo falla, no se crea la orden ni se modifica el inventario. |
| **Dependencias** | REQ-02 (contenido del carrito), REQ-08 (autorización de datos personales), RNF-02 (comportamiento bajo concurrencia). |

Desglose verificable:

| Sub-ID | Descripción | Origen |
| --- | --- | --- |
| REQ-03.1 | La verificación y el descuento de existencias ocurren en la misma transacción que crea la orden. | PDF REQ-03 y apartado 9.3 |
| REQ-03.2 | Si alguna línea no tiene existencias suficientes, la transacción se revierte completa y la respuesta detalla los productos indisponibles. | PDF apartado 9.3: «revierte la transacción completa y responde con el detalle de los productos indisponibles» |
| REQ-03.3 | La orden recibe un identificador único. | PDF REQ-03 |
| REQ-03.4 | Cada variación de existencias originada por una orden queda registrada con origen y fecha. | REQ-06 + PDF Tabla 8 (C-05) |
| REQ-03.5 | `DECISIÓN PROPUESTA` La orden nace en estado `CONFIRMADA` al completarse el checkout simulado; no existe estado intermedio de pago. | El PDF excluye el pago real y REQ-04 indica que «el estado de la orden pasa a confirmada». |

---

## REQ-04 — Checkout simulado

| Campo | Valor |
| --- | --- |
| **ID** | REQ-04 |
| **Tipo** | Funcional |
| **Nombre** | Checkout simulado con aviso explícito |
| **Descripción** | El sistema deberá ejecutar un checkout simulado que informe explícitamente que no se realiza un cobro real y confirme el pedido. |
| **Origen** | Supuesto S-03 / apartado 8 (exclusiones) |
| **Prioridad** | Alta |
| **Criterio de aceptación** | Dada una orden generada, cuando se completa el checkout, entonces la interfaz muestra el aviso de simulación y el estado de la orden pasa a confirmada. |
| **Dependencias** | REQ-03. |

Desglose verificable:

| Sub-ID | Descripción | Origen |
| --- | --- | --- |
| REQ-04.1 | La interfaz advierte que la transacción es una simulación con fines académicos. | PDF apartado 3.3 |
| REQ-04.2 | No se solicitan ni almacenan datos de tarjetas ni de medios de pago. | PDF apartado 3.3 (no aplica PCI DSS) |
| REQ-04.3 | El resultado del checkout es una orden confirmada con su identificador. | Criterio de aceptación REQ-04 |

---

## REQ-05 — Notificación de confirmación

| Campo | Valor |
| --- | --- |
| **ID** | REQ-05 |
| **Tipo** | Funcional |
| **Nombre** | Notificación de confirmación al comprador y al administrador |
| **Descripción** | El sistema deberá enviar una notificación de confirmación al comprador y al administrador con el detalle del pedido. |
| **Origen** | Propietario del micronegocio / alternativa A2 |
| **Prioridad** | Media (candidato a diferirse, PDF apartado 12.3) |
| **Criterio de aceptación** | Dada una orden confirmada, cuando se procesa el evento, entonces ambas partes reciben la notificación con identificador, productos y cantidades en menos de cinco minutos. |
| **Dependencias** | REQ-03, REQ-04; servicio de correo transaccional externo (PDF, apartado 9.3). |

Desglose verificable:

| Sub-ID | Descripción | Origen |
| --- | --- | --- |
| REQ-05.1 | La notificación incluye identificador de la orden, productos y cantidades. | Criterio de aceptación REQ-05 |
| REQ-05.2 | Se entrega en menos de cinco minutos desde la confirmación. | Criterio de aceptación REQ-05 |
| REQ-05.3 | Si el servicio de correo agota su cuota gratuita, la notificación se registra en el sistema y se muestra en el panel, degradando la funcionalidad sin bloquear el flujo. | PDF, riesgo R-08 |
| REQ-05.4 | `DECISIÓN PROPUESTA` El envío es asíncrono: un fallo de notificación nunca revierte ni bloquea una orden ya confirmada. | Consecuencia directa de R-08 («sin bloquear el flujo») y de REQ-03 (la transacción cubre orden e inventario, no el correo). |

---

## REQ-06 — Administración de productos e inventario

| Campo | Valor |
| --- | --- |
| **ID** | REQ-06 |
| **Tipo** | Funcional |
| **Nombre** | Panel de administración de catálogo e inventario con auditoría |
| **Descripción** | El sistema deberá permitir al administrador autenticado crear, editar, despublicar y ajustar existencias de productos, registrando cada variación con origen y fecha. |
| **Origen** | Propietario del micronegocio / causa C-05 (sin proceso definido de actualización de existencias) |
| **Prioridad** | Alta |
| **Criterio de aceptación** | Dado un ajuste manual de inventario, cuando el administrador lo guarda, entonces la existencia se actualiza y queda un registro de auditoría con usuario, valor anterior, valor nuevo y fecha. |
| **Dependencias** | RNF-04 (autenticación y credenciales), RNF-05 (operabilidad del panel). |

Desglose verificable:

| Sub-ID | Descripción | Origen |
| --- | --- | --- |
| REQ-06.1 | Alta, edición y baja (despublicación) de productos. | PDF Tabla 7 y REQ-06 |
| REQ-06.2 | Ajuste manual de existencias. | PDF REQ-06 |
| REQ-06.3 | Toda variación de existencias queda registrada con usuario, valor anterior, valor nuevo, origen y fecha. | Criterio de aceptación REQ-06 + PDF Tabla 8 (C-05) |
| REQ-06.4 | El alta de un producto se realiza en un único formulario, con imagen y existencias. | PDF Tabla 8 (C-04) y RNF-05 |
| REQ-06.5 | Las imágenes del catálogo se almacenan optimizadas (componente C5). | PDF apartado 9.3 y riesgo R-06 |
| REQ-06.6 | `DECISIÓN PROPUESTA` Las existencias se gestionan por variante (talla), no por producto. | El catálogo filtra por talla y debe mostrar disponibilidad real; sin inventario por variante no puede saberse si una talla concreta está agotada. Ver `docs/decisiones/ADR-002-modelo-inventario.md`. |
| REQ-06.7 | `DECISIÓN PROPUESTA` La despublicación no borra el producto ni su histórico de órdenes. | Ley 527 de 1999: la orden debe conservarse íntegra y recuperable (PDF, apartado 3.3). |

---

## REQ-07 — Gestión de órdenes y estados

| Campo | Valor |
| --- | --- |
| **ID** | REQ-07 |
| **Tipo** | Funcional |
| **Nombre** | Listado de órdenes y cambio de estado |
| **Descripción** | El sistema deberá listar las órdenes con su estado y permitir marcarlas como preparadas o entregadas. |
| **Origen** | Personal de apoyo (empaque y despacho) |
| **Prioridad** | Media (candidato a diferirse, PDF apartado 12.3) |
| **Criterio de aceptación** | Dada una orden confirmada, cuando el administrador cambia su estado, entonces el cambio persiste y queda registrado. |
| **Dependencias** | REQ-03; RNF-04 (autenticación); auditoría de REQ-06. |

Desglose verificable:

| Sub-ID | Descripción | Origen |
| --- | --- | --- |
| REQ-07.1 | Listado de órdenes con estado, fecha, contenido y dirección de entrega. | PDF REQ-07 y Tabla 1 (necesidad del personal de apoyo) |
| REQ-07.2 | Transición a `PREPARADA` y a `ENTREGADA`. | PDF REQ-07 |
| REQ-07.3 | Todo cambio de estado queda registrado en auditoría. | Criterio de aceptación REQ-07 + Ley 527 de 1999 (PDF, apartado 3.3) |
| REQ-07.4 | `DECISIÓN PROPUESTA` Transiciones válidas: `CONFIRMADA → PREPARADA → ENTREGADA`, y `CONFIRMADA` o `PREPARADA → CANCELADA`; cancelar devuelve las unidades al inventario dentro de una transacción. | El PDF no define cancelación, pero sin ella una orden errónea dejaría el inventario descuadrado de forma permanente, en contra del objetivo general. Ver RN-13. |

---

## REQ-08 — Autorización de tratamiento de datos personales

| Campo | Valor |
| --- | --- |
| **ID** | REQ-08 |
| **Tipo** | Funcional |
| **Nombre** | Autorización de tratamiento de datos y aviso de privacidad |
| **Descripción** | El sistema deberá solicitar la autorización de tratamiento de datos personales antes de registrar los datos del comprador y enlazar el aviso de privacidad. |
| **Origen** | Ley 1581 de 2012 / restricción R-04 |
| **Prioridad** | Alta |
| **Criterio de aceptación** | Dado el formulario de pedido, cuando el comprador no marca la autorización, entonces la orden no se envía y se indica el motivo. |
| **Dependencias** | REQ-03 (la validación ocurre antes de crear la orden), RNF-04 (minimización de datos). |

Desglose verificable:

| Sub-ID | Descripción | Origen |
| --- | --- | --- |
| REQ-08.1 | La autorización es previa, expresa e informada, y se solicita en el momento de la recolección. | PDF apartado 3.3 |
| REQ-08.2 | El aviso de privacidad y la política de tratamiento son accesibles desde el propio formulario. | PDF apartado 3.3 |
| REQ-08.3 | Solo se recolectan los datos necesarios para entregar el pedido (principio de finalidad). | PDF apartado 3.3 y RNF-04 |
| REQ-08.4 | Existe un canal para atender consultas y reclamos del titular. | PDF apartado 3.3 |
| REQ-08.5 | `DECISIÓN PROPUESTA` La autorización se valida en el servidor y se almacena junto a la orden con fecha y versión del aviso de privacidad. | Sin registro no es demostrable ante el titular ni ante el docente; el PDF exige que el cumplimiento sea «verificable y no una declaración». |

---

## Fuera de alcance (PDF, Tabla 7)

No deben implementarse ni documentarse como pendientes: pasarela de pago real y procesamiento de transacciones, facturación electrónica y reporte tributario, integración con operadores logísticos y seguimiento de envíos, aplicación móvil nativa, multitienda, múltiples monedas e internacionalización, y recomendaciones basadas en aprendizaje automático.
