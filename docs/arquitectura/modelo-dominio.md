# Modelo de dominio

Describe los conceptos del problema **antes** de decidir cómo se guardan, cómo se exponen o cómo se pintan. Fuente: `ProyectoTiendaLocalCUN.pdf`, apartados 3.1 (actores), 5 (problema), 9.1 y 9.3 (flujo y componentes).

## Cuatro planos, cuatro vocabularios

El mismo concepto aparece con nombres distintos según el plano. La regla oficial de nombres está en `../api/convenciones.md`; aquí se fija a qué se refiere cada plano.

| Plano | Qué contiene | Quién lo mantiene |
| --- | --- | --- |
| **Dominio** | Conceptos del negocio: producto, variante, existencias, orden, auditoría. Independiente de tecnología. | Todo el equipo |
| **Persistencia** | Tablas, columnas, claves e índices en PostgreSQL. `snake_case`, singular. | Hedixon Cardozo |
| **API** | Recursos, DTO y códigos de error del contrato REST. `camelCase`. | Contrato compartido (`docs/api/`) |
| **Frontend** | Modelos de vista y estado de pantalla en TypeScript. `camelCase`. | Brandon Soto |

Un nombre de tabla **no tiene por qué ser idéntico** al concepto de dominio ni al del contrato. Ejemplos vigentes en este proyecto:

| Dominio | Persistencia | API | Frontend |
| --- | --- | --- | --- |
| Existencias de una variante | `inventory.stock_quantity` | `availableUnits` | `availableUnits` |
| Producto publicado | `product.published` | `published` | `isPublished` (modelo de vista) |
| Orden | `order_header` (evita la palabra reservada `order`) | `order` | `Order` |
| Registro de auditoría | `audit_log` | `auditEntry` | `AuditEntry` |

---

## Actores

| Actor | Tipo | Responsabilidad en el sistema | Autenticación |
| --- | --- | --- | --- |
| **Comprador** | Persona externa | Consulta el catálogo, arma un carrito, confirma un pedido y aporta sus datos de entrega. | Anónimo |
| **Administrador** | Persona interna (propietario) | Mantiene catálogo e inventario, opera las órdenes y consulta la auditoría. | Sí |
| **Personal de apoyo** | Persona interna | Lee las órdenes confirmadas para empacar y despachar. | Sí (usa el acceso de administrador; ver nota 2 de `../requisitos/historias-usuario.md`) |
| **Equipo de desarrollo** | Externo al flujo de negocio | Interactúa a través del repositorio y del canal de despliegue. | Fuera de la aplicación |
| **Servicio de correo** | Sistema externo | Entrega las notificaciones de confirmación. | Credenciales de servicio |

---

## Entidades del dominio

### Producto (`PRODUCT`)
Artículo que el micronegocio ofrece: nombre, descripción, precio, categoría, imágenes y estado de publicación.
**No tiene existencias propias**: las existencias viven en sus variantes (ADR-002).
Invariantes: un producto publicado tiene al menos una variante (RN-21); despublicar no lo elimina (RN-23).

### Variante de producto (`PRODUCT_VARIANT`)
Combinación vendible del producto; en este alcance la distingue la **talla**. Es la unidad que el comprador agrega al carrito y la que la orden descuenta (RN-05).
Invariantes: talla única dentro del producto; toda variante tiene exactamente un registro de existencias.

### Categoría (`CATEGORY`)
Agrupación del catálogo usada para filtrar (REQ-01). Un producto pertenece a una categoría.

### Existencias (`INVENTORY`)
Número de unidades disponibles de una variante. Es **la fuente única de verdad** del proyecto: el problema central es que hoy esa verdad vive en la memoria del propietario (causa C-01).
Invariantes: nunca negativo (RN-09); solo cambia dentro de una transacción que además registra auditoría (RN-24).

### Orden (`ORDER`)
Compromiso de compra confirmado: número único, líneas, totales, datos de entrega del comprador, constancia de autorización de datos, estado y fechas.
Es un **mensaje de datos con valor probatorio** (Ley 527 de 1999, PDF 3.3): debe conservarse íntegra y recuperable, y todo cambio de estado debe registrarse.
Invariantes: al menos una línea (RN-29); precio congelado al confirmar (RN-28); transiciones acotadas (RN-13).

### Línea de orden (`ORDER_ITEM`)
Cantidad de una variante dentro de una orden, con copia del nombre, la talla y el precio unitario del momento.

### Administrador (`ADMIN_USER`)
Usuario que opera el panel. Guarda credencial derivada, nunca la contraseña (RN-20).

### Registro de auditoría (`AUDIT_LOG`)
Evento que documenta una variación relevante: existencias y estados de orden, con usuario, valores anterior y nuevo, origen y fecha. Corresponde al componente **C6** del PDF y es la fuente de evidencia de los indicadores I-02 e I-03.

### Notificación (`NOTIFICATION`)
Intento de aviso de confirmación al comprador y al administrador, con su estado de envío.
`DECISIÓN PROPUESTA`: el PDF no la modela como entidad, pero el riesgo R-08 exige «registrar la notificación en el sistema y mostrarla en el panel» cuando el correo falla, lo que obliga a persistirla.

### Imagen de producto (`PRODUCT_IMAGE`)
Archivo optimizado asociado a un producto (componente C5). Se almacena ya redimensionado y en formato moderno (RN-22).

### Carrito — concepto **sin entidad persistente**
El PDF define el carrito «con persistencia en sesión» (Tabla 7). Se modela en el cliente; el servidor solo lo valida (RN-06). No existe tabla de carrito ni de reservas.

---

## Relaciones

```text
CATEGORY 1 ──── * PRODUCT
PRODUCT  1 ──── * PRODUCT_VARIANT
PRODUCT  1 ──── * PRODUCT_IMAGE
PRODUCT_VARIANT 1 ──── 1 INVENTORY
PRODUCT_VARIANT 1 ──── * ORDER_ITEM
ORDER    1 ──── * ORDER_ITEM
ORDER    1 ──── * NOTIFICATION
ADMIN_USER 1 ──── * AUDIT_LOG
AUDIT_LOG * ──── 1 (INVENTORY | ORDER)   [referencia polimórfica por tipo de entidad]
```

| Relación | Cardinalidad | Regla asociada |
| --- | --- | --- |
| Categoría → Producto | 1:N | RN-04 |
| Producto → Variante | 1:N | RN-05, RN-21 |
| Variante → Existencias | 1:1 | RN-09 |
| Orden → Línea de orden | 1:N | RN-29 |
| Variante → Línea de orden | 1:N | RN-28 (la línea conserva copia de los datos) |
| Orden → Notificación | 1:N | RN-14, RN-15 |
| Administrador → Auditoría | 1:N | RN-24, RN-27 |

---

## Responsabilidades por concepto

| Concepto | Decide | No decide |
| --- | --- | --- |
| Existencias | Si una venta puede confirmarse | Cómo se muestra el catálogo |
| Orden | Qué se comprometió, a quién se entrega y en qué estado está | Cómo se cobra (fuera de alcance) |
| Auditoría | Qué ocurrió y cuándo | Qué debe ocurrir |
| Catálogo | Qué se ofrece y cómo se encuentra | Si hay unidades (consulta a existencias) |

---

## Ubicación de las reglas

| Regla | Dónde vive | Por qué |
| --- | --- | --- |
| Validación de formato de entrada | API (esquemas de petición) | Rechazo temprano y respuesta uniforme |
| Reglas de negocio (RN-01 … RN-29) | Capa de lógica de negocio del backend | Deben cumplirse aunque el cliente cambie |
| Atomicidad y bloqueo (RN-08, RN-10) | Transacción en la base de datos | Única forma de garantizarlo bajo concurrencia |
| Invariante de no-negatividad (RN-09) | Restricción `CHECK` en la base de datos **y** validación en el backend | Defensa en profundidad |
| Presentación de disponibilidad | Frontend, a partir de la respuesta de la API | El frontend no calcula reglas, las muestra |

> El frontend nunca es autoridad: «ninguna comprobación de existencias hecha en el navegador es vinculante» (PDF, apartado 9.3).
