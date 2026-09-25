# Criterios de aceptación

Catálogo único de criterios en formato **Dado / Cuando / Entonces**. Los criterios `CA-xx-0` son literales del PDF (Tabla 10) y no se alteran; los numerados `.1`, `.2`, … son criterios derivados que el equipo añade para hacer verificable el detalle de implementación y se marcan `DECISIÓN PROPUESTA` cuando no se deducen directamente del texto original.

Cada criterio indica la prueba que lo verifica (ver `docs/pruebas/casos-prueba.md`).

---

## REQ-01 — Catálogo

| ID | Criterio | Prueba |
| --- | --- | --- |
| CA-01-0 | **Dado** un catálogo con productos disponibles y agotados, **cuando** el comprador aplica un filtro, **entonces** se muestran solo los productos que cumplen el criterio y cada uno indica su disponibilidad actual. | CP-01, CP-02 |
| CA-01-1 | **Dado** un catálogo con productos publicados y despublicados, **cuando** se consulta el listado público, **entonces** solo aparecen los publicados. | CP-03 |
| CA-01-2 | **Dado** un término de búsqueda que coincide parcialmente con el nombre de un producto, **cuando** el comprador busca, **entonces** el producto aparece en los resultados sin distinción de mayúsculas ni de tildes. `DECISIÓN PROPUESTA` | CP-04 |
| CA-01-3 | **Dado** un producto con variantes de talla, **cuando** el comprador abre el detalle, **entonces** ve cada talla con su disponibilidad actual. | CP-05 |
| CA-01-4 | **Dado** un producto cuyas variantes están todas en cero, **cuando** aparece en el listado, **entonces** se muestra marcado como agotado y no puede agregarse. `DECISIÓN PROPUESTA` | CP-06 |
| CA-01-5 | **Dado** un filtro por categoría combinado con un filtro por talla, **cuando** se aplican juntos, **entonces** el resultado contiene solo productos que cumplen ambas condiciones. | CP-02 |

## REQ-02 — Carrito

| ID | Criterio | Prueba |
| --- | --- | --- |
| CA-02-0 | **Dado** un producto con cero unidades, **cuando** el comprador intenta agregarlo, **entonces** el sistema lo impide y muestra el motivo. | CP-10 |
| CA-02-1 | **Dada** una variante con 3 unidades, **cuando** el comprador intenta agregar 5, **entonces** el sistema rechaza la cantidad e informa cuántas hay disponibles. `DECISIÓN PROPUESTA` | CP-11 |
| CA-02-2 | **Dado** un carrito con productos, **cuando** el comprador recarga la página, **entonces** el carrito conserva su contenido en la sesión. | CP-12 |
| CA-02-3 | **Dado** un carrito cuya variante quedó agotada después de agregarla, **cuando** el comprador revalida antes de confirmar, **entonces** el sistema marca esa línea como indisponible y no permite continuar hasta corregirla. `DECISIÓN PROPUESTA` | CP-13 |

## REQ-03 — Orden y descuento de inventario

| ID | Criterio | Prueba |
| --- | --- | --- |
| CA-03-0 | **Dado** un carrito válido, **cuando** el comprador confirma, **entonces** se crea la orden y las existencias se reducen en la misma cantidad; si algo falla, no se crea la orden ni se modifica el inventario. | CP-20, CP-21 |
| CA-03-1 | **Dada** una orden creada, **cuando** se consulta su identificador, **entonces** es único y permite recuperar la orden íntegra. | CP-22 |
| CA-03-2 | **Dado** un carrito con dos líneas, una disponible y otra agotada, **cuando** se confirma, **entonces** no se crea la orden, no se descuenta ninguna unidad y la respuesta detalla la línea indisponible. | CP-23 |
| CA-03-3 | **Dada** una orden confirmada, **cuando** se consulta la auditoría, **entonces** existe un registro por cada variación de existencias con origen `ORDEN` y fecha. | CP-24 |

## REQ-04 — Checkout simulado

| ID | Criterio | Prueba |
| --- | --- | --- |
| CA-04-0 | **Dada** una orden generada, **cuando** se completa el checkout, **entonces** la interfaz muestra el aviso de simulación y el estado de la orden pasa a confirmada. | CP-30 |
| CA-04-1 | **Dado** el flujo de checkout, **cuando** se inspeccionan el formulario y la API, **entonces** no existe ningún campo de tarjeta ni de medio de pago. | CP-31 |

## REQ-05 — Notificación

| ID | Criterio | Prueba |
| --- | --- | --- |
| CA-05-0 | **Dada** una orden confirmada, **cuando** se procesa el evento, **entonces** ambas partes reciben la notificación con identificador, productos y cantidades en menos de cinco minutos. | CP-40 |
| CA-05-1 | **Dado** un servicio de correo que responde con error o cuota agotada, **cuando** se intenta notificar, **entonces** la notificación queda registrada como fallida y visible en el panel, y la orden permanece confirmada. | CP-41 |

## REQ-06 — Administración de productos e inventario

| ID | Criterio | Prueba |
| --- | --- | --- |
| CA-06-0 | **Dado** un ajuste manual de inventario, **cuando** el administrador lo guarda, **entonces** la existencia se actualiza y queda un registro de auditoría con usuario, valor anterior, valor nuevo y fecha. | CP-50 |
| CA-06-1 | **Dado** un usuario no autenticado, **cuando** invoca cualquier operación de administración, **entonces** la API responde 401 y no modifica datos. | CP-51 |
| CA-06-2 | **Dado** un producto publicado, **cuando** el administrador lo despublica, **entonces** desaparece del catálogo público y sigue existiendo en la administración y en las órdenes previas. | CP-52 |
| CA-06-3 | **Dado** un ajuste que dejaría la existencia por debajo de cero, **cuando** se intenta guardar, **entonces** el sistema lo rechaza. `DECISIÓN PROPUESTA` | CP-53 |
| CA-06-4 | **Dada** una imagen cargada por el administrador, **cuando** se almacena, **entonces** se guarda optimizada y con las dimensiones previstas para el catálogo. | CP-54 |

## REQ-07 — Órdenes y estados

| ID | Criterio | Prueba |
| --- | --- | --- |
| CA-07-0 | **Dada** una orden confirmada, **cuando** el administrador cambia su estado, **entonces** el cambio persiste y queda registrado. | CP-60 |
| CA-07-1 | **Dada** una orden entregada, **cuando** se intenta devolverla a preparada, **entonces** el sistema rechaza la transición. `DECISIÓN PROPUESTA` | CP-61 |
| CA-07-2 | **Dada** una orden confirmada, **cuando** el administrador la cancela, **entonces** las unidades vuelven al inventario en la misma transacción y queda registro de auditoría. `DECISIÓN PROPUESTA` | CP-62 |

## REQ-08 — Datos personales

| ID | Criterio | Prueba |
| --- | --- | --- |
| CA-08-0 | **Dado** el formulario de pedido, **cuando** el comprador no marca la autorización, **entonces** la orden no se envía y se indica el motivo. | CP-70 |
| CA-08-1 | **Dado** el formulario de pedido, **cuando** se renderiza, **entonces** el aviso de privacidad y la política de tratamiento son accesibles desde el propio formulario. | CP-71 |
| CA-08-2 | **Dada** una orden creada con autorización, **cuando** se consulta el registro, **entonces** consta la fecha y la versión del aviso aceptado. `DECISIÓN PROPUESTA` | CP-72 |
| CA-08-3 | **Dada** una petición de creación de orden sin el consentimiento, **cuando** llega directamente a la API sin pasar por el formulario, **entonces** la API la rechaza con `CONSENT_REQUIRED`. `DECISIÓN PROPUESTA` | CP-73 |

---

## Criterios no funcionales

| ID | Criterio | Prueba |
| --- | --- | --- |
| CA-RNF-01 | **Dada** una medición con herramienta de auditoría de rendimiento en tres ejecuciones, **cuando** se promedian los resultados, **entonces** el peso transferido y el tiempo de renderizado no superan los umbrales (≤ 1,5 MB, < 3 s). | CP-80 |
| CA-RNF-02 | **Dadas** 50 solicitudes simultáneas sobre un producto con 10 unidades, **cuando** se ejecuta la prueba de concurrencia, **entonces** se confirman exactamente 10 órdenes, las 40 restantes reciben respuesta de indisponibilidad y la existencia final es cero. | CP-90 |
| CA-RNF-03 | **Dada** una auditoría automatizada más revisión manual de las cuatro pautas, **cuando** se ejecuta sobre las pantallas del flujo principal, **entonces** no se registran incumplimientos de nivel A ni AA en esos criterios. | CP-81 |
| CA-RNF-04 | **Dada** una revisión de configuración y del esquema de datos, **cuando** se inspeccionan, **entonces** todo el tráfico usa TLS, ninguna contraseña está en texto claro y no existen campos personales sin finalidad declarada. | CP-82 |
| CA-RNF-05 | **Dada** una prueba de usabilidad con cinco participantes del perfil, **cuando** ejecutan la tarea, **entonces** al menos cuatro la completan sin ayuda en menos de cinco minutos. | CP-83 |
| CA-RNF-06 | **Dada** la construcción de la imagen en el canal automatizado, **cuando** finaliza, **entonces** el tamaño reportado es inferior a 250 MB y el despliegue se completa sin pasos manuales. | CP-84 |

---

## Criterios de aceptación de los objetivos específicos (PDF, Tabla 6)

| Objetivo | Criterio de aceptación |
| --- | --- |
| OE-1 | El documento registra los cuatro indicadores de línea base del apartado 14 y está validado por el propietario del micronegocio. |
| OE-2 | Todo requisito tiene identificador, origen, prioridad y criterio de aceptación verificable; el modelo soporta los casos de uso del alcance. |
| OE-3 | Un cambio integrado en la rama principal llega al ambiente desplegado sin intervención manual y el flujo de trabajo falla si una prueba falla. |
| OE-4 | Se cumplen los criterios de RNF-01 a RNF-05 o se documenta la desviación con su causa y su plan de corrección. |

> El criterio de OE-2 es el que audita esta fase: `docs/VALIDATION-REPORT.md` verifica que se cumpla.
