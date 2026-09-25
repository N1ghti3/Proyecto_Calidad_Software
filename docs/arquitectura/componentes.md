# Componentes

Ficha de cada componente del PDF (apartado 9.3) con su responsabilidad, sus interfaces, su responsable y los requisitos que sostiene.

| ID | Componente | Responsable | Requisitos |
| --- | --- | --- | --- |
| C1 | Frontend web responsivo | Brandon Soto | REQ-01…REQ-04, REQ-06, REQ-07, REQ-08, RNF-01, RNF-03, RNF-05 |
| C2 | Proxy inverso | Jhon Ortiz | RNF-01, RNF-04 |
| C3 | API REST | Hedixon Cardozo | REQ-01…REQ-08, RNF-02, RNF-04 |
| C4 | Base de datos relacional | Hedixon Cardozo | REQ-03, REQ-06, RNF-02 |
| C5 | Almacenamiento de imágenes | Hedixon Cardozo / Jhon Ortiz | REQ-01, REQ-06, RNF-01 |
| C6 | Registro de auditoría | Hedixon Cardozo | REQ-06, REQ-07 |
| S1 | Servicio de correo transaccional (externo) | Jhon Ortiz (configuración) | REQ-05 |
| S3 | Plataforma de automatización (externo) | Jhon Ortiz | RNF-06, OE-3 |

---

## C1 — Frontend web responsivo

**Responsabilidad (PDF):** renderiza el catálogo y el carrito; no contiene reglas de negocio y confía la validación al servidor.

| Aspecto | Detalle |
| --- | --- |
| Pantallas públicas | Listado de catálogo, detalle de producto, carrito, checkout (datos + consentimiento), confirmación, consulta de orden |
| Pantallas administrativas | Inicio de sesión, lista de productos, formulario único de producto, ajuste de existencias, lista de órdenes, detalle de orden, auditoría, notificaciones |
| Entradas | Respuestas de C3 según `../api/modelos.md` |
| Salidas | Peticiones a C3 según `../api/endpoints.md` |
| Estado propio | Contenido del carrito en sesión (RN-06), filtros aplicados, token de sesión del administrador |
| Restricciones | Presupuesto de peso de RNF-01; WCAG 2.2 AA en las cuatro pautas (RNF-03); enfoque Mobile First (O-03) |
| Prohibido | Decidir disponibilidad, calcular totales como fuente de verdad, ocultar errores de negocio |

Los estados que debe implementar cada pantalla están en [`../api/frontend-backend-contract.md`](../api/frontend-backend-contract.md).

---

## C2 — Proxy inverso

**Responsabilidad (PDF):** termina la conexión cifrada, comprime las respuestas y sirve los activos estáticos con encabezados de caché.

| Aspecto | Detalle |
| --- | --- |
| Entradas | Tráfico HTTPS de compradores y administradores |
| Salidas | Activos estáticos de C1; proxy hacia C3 en `/api` |
| Contribución a RNF-01 | Compresión de texto, caché de activos con huella de contenido, HTTP/2 |
| Contribución a RNF-04 | Terminación TLS; redirección de HTTP a HTTPS; cabeceras de seguridad |
| Prohibido | Contener lógica de negocio o de autorización |

---

## C3 — API REST

**Responsabilidad (PDF):** autenticación del administrador, gestión del catálogo y —el elemento crítico— la generación de la orden dentro de una transacción que verifica y descuenta las existencias de manera atómica.

Estructura interna (`DECISIÓN PROPUESTA`, ADR-001):

| Subcapa | Contenido | Regla |
| --- | --- | --- |
| Interfaz (routers) | Rutas, validación de formato, autenticación, códigos HTTP | No contiene reglas de negocio |
| Servicios | RN-01 … RN-29, transacciones, orquestación de notificaciones | No conoce HTTP |
| Repositorios | Consultas parametrizadas, bloqueos, acceso a C4 | No decide reglas |
| Esquemas | Contratos de petición y respuesta (`../api/modelos.md`) | Única fuente de nombres de la API |

| Aspecto | Detalle |
| --- | --- |
| Interfaces expuestas | `/api/v1/...` (ver `../api/endpoints.md`) |
| Dependencias | C4 (obligatoria), C5 (imágenes), C6 (auditoría), S1 (correo, opcional y degradable) |
| Operación crítica | Confirmación de orden (RN-08, RN-10, RN-11) |
| Errores | Estructura única de `../api/errores.md` |

---

## C4 — Base de datos relacional (PostgreSQL)

**Responsabilidad (PDF):** garantizar atomicidad, consistencia, aislamiento y durabilidad. El PDF descarta expresamente una base documental sin transacciones multidocumento.

| Aspecto | Detalle |
| --- | --- |
| Esquema | `../arquitectura/modelo-relacional.md` |
| Invariantes | `CHECK (stock_quantity >= 0)`; unicidad de `order_number`, `sku`, `slug`; claves foráneas con `RESTRICT` sobre datos históricos |
| Concurrencia | Bloqueo de fila sobre `inventory` durante la confirmación (ADR-005) |
| Datos personales | Solo los campos con finalidad declarada (RN-17) |
| Prohibido | Lógica de negocio en procedimientos almacenados (mantener la regla en un solo lugar) |

---

## C5 — Almacenamiento de imágenes optimizadas

**Responsabilidad (PDF):** almacena las imágenes del catálogo ya optimizadas.

| Aspecto | Detalle |
| --- | --- |
| Entrada | Imagen cargada por el administrador (EP-16) |
| Proceso | Conversión a formato moderno y redimensionado en el servidor al cargar (RN-22, riesgo R-06) |
| Salida | Archivo servido por C2 con encabezados de caché |
| Restricción | Contribuye al presupuesto de ≈ 1 000 KB de imágenes de RNF-01 |

---

## C6 — Registro de auditoría y eventos

**Responsabilidad (PDF):** registra los eventos de orden, inventario y despliegue; es la fuente de evidencia para los indicadores del apartado 14.

| Aspecto | Detalle |
| --- | --- |
| Eventos de aplicación | Variaciones de existencias (RN-24) y cambios de estado de orden (RN-27), en `audit_log` |
| Eventos de despliegue | Registro de ejecuciones del canal automatizado (indicador I-06), fuera de la base de datos |
| Consulta | EP-19, solo administrador |
| Invariante | Solo anexado (RN-25) |
| Indicadores que alimenta | I-02 (consistencia), I-03 (trazabilidad de pedidos) |

---

## Sistemas externos

| ID | Sistema | Uso | Degradación prevista |
| --- | --- | --- | --- |
| S1 | Servicio de correo transaccional | Notificación de confirmación (REQ-05) | Si agota cuota: notificación en estado `FALLIDA`, visible en el panel; la orden no se bloquea (RN-15, riesgo R-08) |
| S2 | Pasarela de pago | **Fuera de alcance** (línea punteada en el PDF) | No se implementa; el checkout es simulado (RN-12) |
| S3 | Plataforma de automatización | Construcción de imagen y despliegue por SSH | Dependencia crítica D-01; prueba de concepto en la semana 4 |

---

## Matriz componente × requisito

| Requisito | C1 | C2 | C3 | C4 | C5 | C6 | S1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| REQ-01 | ● | ○ | ● | ● | ● | | |
| REQ-02 | ● | | ● | ● | | | |
| REQ-03 | ● | | ● | ● | | ● | |
| REQ-04 | ● | | ● | ● | | | |
| REQ-05 | ○ | | ● | ● | | | ● |
| REQ-06 | ● | | ● | ● | ● | ● | |
| REQ-07 | ● | | ● | ● | | ● | |
| REQ-08 | ● | | ● | ● | | | |
| RNF-01 | ● | ● | ○ | | ● | | |
| RNF-02 | | | ● | ● | | ● | |
| RNF-03 | ● | | | | | | |
| RNF-04 | ○ | ● | ● | ● | | | |
| RNF-05 | ● | | ○ | | | | |
| RNF-06 | ○ | ● | ● | ● | ○ | | |

● responsabilidad principal ○ contribución parcial
