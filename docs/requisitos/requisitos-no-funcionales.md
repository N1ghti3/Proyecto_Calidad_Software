# Requisitos no funcionales

**Fuente principal:** `ProyectoTiendaLocalCUN.pdf` — apartado 10, Tabla 10. La clasificación sigue las características del modelo de calidad del producto de **ISO/IEC 25010:2023**, tal como lo establece el documento.

Los identificadores (`RNF-01` … `RNF-06`), la característica de calidad, el origen, la prioridad y el criterio de aceptación son del PDF. Lo añadido por el equipo se marca `DECISIÓN PROPUESTA`.

> Nota del PDF: «Los umbrales de RNF-01 y RNF-06 son metas iniciales del equipo y podrán ajustarse con justificación tras la primera medición».

| ID | Característica ISO/IEC 25010:2023 | Prioridad | Umbral |
| --- | --- | --- | --- |
| RNF-01 | Eficiencia de desempeño | Alta | ≤ 1,5 MB primera carga; < 3 s contenido principal |
| RNF-02 | Fiabilidad e integridad | Alta | Ninguna orden confirmada excede las existencias |
| RNF-03 | Capacidad de interacción — accesibilidad | Media | WCAG 2.2 nivel AA en cuatro pautas |
| RNF-04 | Seguridad y confidencialidad | Alta | HTTPS, credenciales derivadas, minimización de datos |
| RNF-05 | Capacidad de interacción — operabilidad | Media | 4 de 5 participantes completan el alta sin ayuda en < 5 min |
| RNF-06 | Flexibilidad — capacidad de instalación | Media | Imagen de aplicación < 250 MB, despliegue sin pasos manuales |

---

## RNF-01 — Eficiencia de desempeño

| Campo | Valor |
| --- | --- |
| **ID** | RNF-01 |
| **Tipo** | No funcional — eficiencia de desempeño |
| **Descripción** | El catálogo deberá transferir como máximo 1,5 MB en su primera carga y renderizar el contenido principal en menos de 3 s en un dispositivo móvil de gama media con conexión 4G simulada. |
| **Origen** | Oportunidad O-03 (acceso mayoritariamente móvil) / Green IT |
| **Prioridad** | Alta |
| **Criterio de aceptación** | Dada una medición con herramienta de auditoría de rendimiento en tres ejecuciones, cuando se promedian los resultados, entonces el peso transferido y el tiempo de renderizado no superan los umbrales definidos. |
| **Dependencias** | REQ-01 (pantallas medidas), riesgo R-06 (imágenes sin optimizar), REQ-06.5 (optimización de imágenes en el servidor). |
| **Verificación** | Indicador I-04; auditoría de rendimiento, promedio de tres ejecuciones. |

Implicaciones de diseño declaradas en el PDF (apartados 3.2 y 9.3): enfoque Mobile First, presupuesto estricto de peso de página, formato de imagen moderno, carga diferida, tamaño del paquete de JavaScript acotado, compresión y encabezados de caché en el proxy inverso (C2).

`DECISIÓN PROPUESTA` — Reparto del presupuesto de 1,5 MB para que frontend y backend puedan trabajar por separado sin renegociarlo:

| Recurso | Presupuesto | Responsable |
| --- | --- | --- |
| JavaScript (comprimido) | ≤ 250 KB | Frontend |
| CSS (comprimido) | ≤ 60 KB | Frontend |
| Fuentes | ≤ 100 KB | Frontend |
| Imágenes del listado (12 productos) | ≤ 1 000 KB (≈ 80 KB por tarjeta) | Backend (optimización al cargar) + Frontend (tamaños y carga diferida) |
| Otros (HTML, JSON del listado) | ≤ 90 KB | Ambos |

Justificación: el PDF fija el total pero no el reparto; sin reparto, cualquier exceso sería una discusión sin criterio. Los valores suman 1,5 MB y deben reajustarse tras la primera medición (fin de I-3).

---

## RNF-02 — Fiabilidad e integridad (requisito central del proyecto)

| Campo | Valor |
| --- | --- |
| **ID** | RNF-02 |
| **Tipo** | No funcional — fiabilidad e integridad |
| **Descripción** | Ninguna orden confirmada podrá exceder las existencias disponibles bajo acceso concurrente. |
| **Origen** | Causa C-01 / subpregunta SP-1 |
| **Prioridad** | Alta (núcleo no negociable) |
| **Criterio de aceptación** | Dadas 50 solicitudes simultáneas sobre un producto con 10 unidades, cuando se ejecuta la prueba de concurrencia, entonces se confirman exactamente 10 órdenes, las 40 restantes reciben respuesta de indisponibilidad y la existencia final es cero. |
| **Dependencias** | REQ-03; riesgo R-03; componentes C3 y C4. |
| **Verificación** | Indicador I-02; `docs/pruebas/pruebas-concurrencia.md`. |

Además de requisito de calidad, el PDF lo trata como **condición de cumplimiento legal**: informar disponibilidad inexacta contraviene el deber de información veraz de la Ley 1480 de 2011 (apartado 3.3).

Mecanismo previsto por el PDF (apartado 9.3): base de datos relacional con transacciones ACID y **bloqueo a nivel de fila** sobre el registro de existencias. La decisión técnica detallada está en `docs/decisiones/ADR-005-concurrencia.md`.

---

## RNF-03 — Accesibilidad

| Campo | Valor |
| --- | --- |
| **ID** | RNF-03 |
| **Tipo** | No funcional — capacidad de interacción (accesibilidad) |
| **Descripción** | El catálogo y el formulario de pedido deberán cumplir WCAG 2.2 nivel AA en contraste, texto alternativo, navegación por teclado y etiquetado de formularios. |
| **Origen** | W3C (2023) / restricción R-04 |
| **Prioridad** | Media (candidato a diferirse, PDF apartado 12.3) |
| **Criterio de aceptación** | Dada una auditoría automatizada más revisión manual de las cuatro pautas, cuando se ejecuta sobre las pantallas del flujo principal, entonces no se registran incumplimientos de nivel A ni AA en esos criterios. |
| **Dependencias** | REQ-01, REQ-02, REQ-04, REQ-08 (pantallas del flujo principal). |
| **Verificación** | Indicador I-08; auditoría automatizada + revisión manual. |

El PDF precisa que no existe obligación legal para un comercio privado en Colombia (la Resolución 1519 de 2020 vincula al sector público) y que el equipo adopta WCAG voluntariamente como criterio de calidad. El alcance evaluado son **las cuatro pautas listadas**, no la norma completa.

---

## RNF-04 — Seguridad y confidencialidad

| Campo | Valor |
| --- | --- |
| **ID** | RNF-04 |
| **Tipo** | No funcional — seguridad y confidencialidad |
| **Descripción** | El sistema deberá operar sobre HTTPS, almacenar las credenciales del administrador con función de derivación de clave y recolectar únicamente los datos necesarios para la entrega. |
| **Origen** | Ley 1581 de 2012 |
| **Prioridad** | Alta |
| **Criterio de aceptación** | Dada una revisión de configuración y del esquema de datos, cuando se inspeccionan, entonces todo el tráfico usa TLS, ninguna contraseña está en texto claro y no existen campos personales sin finalidad declarada. |
| **Dependencias** | REQ-06 (autenticación del administrador), REQ-08 (autorización del titular), componente C2 (terminación TLS). |
| **Verificación** | Revisión de configuración y de esquema; `docs/pruebas/estrategia-pruebas.md` (campaña de seguridad). |

Controles mínimos que el PDF adopta con base en OWASP Top 10 (2021) — apartado 12.4:

- consultas parametrizadas;
- validación en el servidor;
- almacenamiento de credenciales mediante función de derivación de clave;
- gestión de secretos fuera del repositorio (riesgo R-07);
- cifrado en tránsito.

`DECISIÓN PROPUESTA` — Datos personales recolectados, con su finalidad declarada (principio de minimización): nombre del comprador, un medio de contacto (correo electrónico), teléfono, dirección de entrega y ciudad. El PDF menciona «nombre, teléfono o correo y dirección de entrega»; el correo se hace obligatorio porque REQ-05 exige notificar al comprador. Ver `docs/arquitectura/modelo-relacional.md`.

---

## RNF-05 — Operabilidad del panel de administración

| Campo | Valor |
| --- | --- |
| **ID** | RNF-05 |
| **Tipo** | No funcional — capacidad de interacción (operabilidad) |
| **Descripción** | Un propietario sin formación técnica deberá completar el alta de un producto con imagen y existencias sin asistencia. |
| **Origen** | Causa C-04 (baja madurez digital) / OE-4 |
| **Prioridad** | Media |
| **Criterio de aceptación** | Dada una prueba de usabilidad con cinco participantes del perfil, cuando ejecutan la tarea, entonces al menos cuatro la completan sin ayuda en menos de cinco minutos. |
| **Dependencias** | REQ-06.4 (formulario único). |
| **Verificación** | Indicador I-05; prueba de usabilidad (semana 13, condicionada a disponibilidad de participantes). |

---

## RNF-06 — Capacidad de instalación (contenedores)

| Campo | Valor |
| --- | --- |
| **ID** | RNF-06 |
| **Tipo** | No funcional — flexibilidad / capacidad de instalación |
| **Descripción** | El sistema deberá desplegarse de forma reproducible mediante contenedores, con imagen de aplicación inferior a 250 MB. |
| **Origen** | Green IT / DevOps |
| **Prioridad** | Media |
| **Criterio de aceptación** | Dada la construcción de la imagen en el canal automatizado, cuando finaliza, entonces el tamaño reportado es inferior al umbral y el despliegue se completa sin pasos manuales. |
| **Dependencias** | Canal de integración y despliegue continuos; dependencia crítica D-01 (acceso SSH a la instancia). |
| **Verificación** | Indicadores I-06 e I-07; salida de la construcción en el canal automatizado. |

---

## Restricciones del proyecto que condicionan estos requisitos (PDF, apartado 8)

| ID | Restricción |
| --- | --- |
| R-01 | El micronegocio no dispone de infraestructura ni de personal técnico: el sistema lo opera el equipo; el negocio solo usa un navegador. |
| R-02 | Habilitar una pasarela de pago real exige requisitos jurídicos y tiempos externos: checkout simulado. |
| R-03 | Presupuesto nulo: solo componentes de código abierto y servicios de capa gratuita. |
| R-04 | Obligaciones de habeas data e información veraz al consumidor. |
| R-05 | Semestre de dieciséis semanas con tres integrantes a tiempo parcial. |

Supuestos por validar: **S-01** (participación del micronegocio), **S-02** (capa gratuita de AWS), **S-03** (aceptación del checkout simulado). Dependencia crítica: **D-01** (acceso SSH a la instancia).
