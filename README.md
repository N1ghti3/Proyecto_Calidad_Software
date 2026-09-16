# TiendaLocal

> **Estado del proyecto:** Fase 0 — Inicialización del repositorio.
> Este repositorio aún no contiene código de la aplicación.

## Descripción

TiendaLocal es una plataforma web **D2C (Direct to Consumer)** para micronegocios de moda urbana y artesanías en Bogotá D.C.

Su propósito es ofrecer un canal donde los compradores puedan consultar productos y realizar pedidos, mientras que los administradores del negocio gestionan productos, inventario y órdenes desde una única fuente de información confiable.

Es un proyecto académico desarrollado por un equipo de 3 integrantes.

## Contexto

Muchos pequeños negocios administran actualmente sus productos e inventario mediante redes sociales, aplicaciones de mensajería, memoria, hojas de cálculo u otros mecanismos manuales.

El problema principal es la **falta de una fuente única y confiable para conocer el inventario disponible**. Esto puede provocar:

- ventas de productos agotados;
- inconsistencias entre el inventario real y el publicado;
- errores humanos;
- dificultad para administrar pedidos;
- falta de trazabilidad;
- problemas cuando varios compradores intentan adquirir simultáneamente las mismas unidades.

## Objetivo general

Construir una plataforma web D2C para micronegocios de moda urbana y artesanías que permita administrar catálogo, inventario y pedidos, garantizando principalmente la consistencia del inventario cuando existen compras simultáneas.

## Objetivos específicos

El sistema posteriormente deberá permitir:

- Mostrar un catálogo de productos.
- Buscar productos.
- Filtrar productos.
- Consultar detalles de productos.
- Agregar productos al carrito.
- Validar disponibilidad.
- Crear órdenes.
- Descontar inventario correctamente.
- Evitar inventario negativo.
- Gestionar productos desde un panel administrativo.
- Gestionar existencias.
- Gestionar estados de las órdenes.
- Registrar auditoría de cambios importantes.
- Realizar un checkout simulado.
- Enviar notificaciones de confirmación.
- Proteger los datos personales de los compradores.

## Alcance

### Incluye

- Catálogo de productos.
- Búsqueda.
- Filtros.
- Carrito.
- Órdenes.
- Checkout simulado.
- Administración de productos.
- Administración de inventario.
- Administración de pedidos.
- Auditoría.
- Notificaciones.
- Autenticación administrativa.
- Seguridad.
- Pruebas.
- Docker.
- CI/CD.
- Despliegue.

### No incluye

- Pagos reales.
- Pasarelas de pago reales.
- Facturación electrónica.
- Integración logística.
- Seguimiento de envíos.
- Aplicación móvil nativa.
- Machine Learning.
- Recomendaciones mediante IA.
- Multitienda.
- Múltiples monedas.

> El checkout será **exclusivamente una simulación académica**.

## Usuarios

### Comprador

Podrá posteriormente:

- consultar el catálogo;
- buscar;
- filtrar;
- consultar productos;
- agregar productos al carrito;
- realizar checkout;
- recibir confirmación de la orden.

No será obligatorio crear una cuenta para consultar el catálogo.

### Administrador

Podrá posteriormente:

- autenticarse;
- administrar productos;
- publicar/despublicar productos;
- administrar inventario;
- visualizar órdenes;
- cambiar estados de órdenes;
- consultar auditoría.

## Problema crítico

El principal reto técnico del proyecto es la **consistencia del inventario bajo concurrencia**. El sistema debe manejar múltiples solicitudes simultáneas sobre las mismas unidades sin generar sobreventa ni inconsistencias.

### Ejemplo de referencia

| Condición / Resultado | Valor |
| --- | --- |
| Inventario inicial | 10 unidades |
| Solicitudes simultáneas (1 unidad cada una) | 50 |
| Órdenes confirmadas esperadas | **10** |
| Solicitudes rechazadas esperadas | **40** |
| Stock final esperado | **0** |

Nunca debe ocurrir:

- inventario negativo;
- más de 10 órdenes confirmadas;
- pérdida de unidades;
- inconsistencias entre órdenes e inventario.

Esta funcionalidad se implementará posteriormente mediante transacciones y mecanismos apropiados de control de concurrencia en PostgreSQL.

> ⚠️ **Todavía no está implementado.** En esta fase solo se documenta como objetivo técnico del proyecto.

## Requisitos

### Requisitos funcionales principales

| ID | Requisito |
| --- | --- |
| REQ-01 | Catálogo de productos con listado, detalle, búsqueda, categorías, tallas y disponibilidad. |
| REQ-02 | Agregar productos al carrito validando disponibilidad. |
| REQ-03 | Crear órdenes y descontar inventario de manera atómica. |
| REQ-04 | Checkout simulado. |
| REQ-05 | Notificación de confirmación de pedido. |
| REQ-06 | Administración de productos e inventario. |
| REQ-07 | Administración de órdenes y estados. |
| REQ-08 | Protección y autorización para el tratamiento de datos personales. |

### Requisitos no funcionales principales

| Categoría | Requisitos |
| --- | --- |
| Rendimiento | Primera carga ≤ 1.5 MB transferidos. Contenido principal < 3 segundos. |
| Seguridad | Protección de credenciales. Password hashing. Autenticación. Autorización. Validación de entradas. Protección contra SQL Injection. HTTPS en producción. Secrets mediante variables de entorno. |
| Accesibilidad | WCAG 2.2 AA. Navegación por teclado. Contraste adecuado. Texto alternativo. Formularios accesibles. |
| Concurrencia | Control transaccional del inventario. Nunca permitir stock negativo. Pruebas de concurrencia. |
| Docker | Imagen de aplicación idealmente inferior a 250 MB. |

Estos requisitos se implementarán y verificarán posteriormente.

## Arquitectura prevista

> La siguiente arquitectura es **prevista**; no está implementada.

```text
Frontend
   ↓
Nginx / Reverse Proxy
   ↓
API REST
   ↓
PostgreSQL
```

Componentes adicionales previstos:

- almacenamiento/optimización de imágenes;
- auditoría;
- servicio de correo/notificaciones;
- Docker;
- GitHub Actions;
- AWS.

## Stack tecnológico previsto

> Ninguna de estas tecnologías está instalada ni configurada todavía.

| Capa | Tecnologías |
| --- | --- |
| Frontend | React + TypeScript + Vite |
| Backend | Python + FastAPI (SQLAlchemy, Pydantic) |
| Database | PostgreSQL |
| Infrastructure | Docker + Docker Compose + Nginx + AWS (EC2) |
| Testing | Pytest + pruebas de integración + E2E (cuando corresponda) + pruebas de concurrencia + Lighthouse |
| CI/CD | GitHub Actions |

## Equipo

| Integrante      | Área             | Responsabilidad                                |
| --------------- | ---------------- | ---------------------------------------------- |
| Brandon Soto     | Frontend         | Desarrollo frontend y UX/UI                    |
| Hedixon Cardozo | Backend          | API, lógica de negocio y base de datos         |
| Jhon Ortiz      | DevOps / Calidad | Docker, CI/CD, testing, despliegue y seguridad |

### Detalle de responsabilidades

**Brandon Soto — Frontend**
Carpeta principal: `/frontend`

- Aplicación frontend.
- Catálogo, búsqueda, filtros y detalle de producto.
- Carrito, checkout y confirmación.
- Panel administrativo.
- Diseño responsive.
- Accesibilidad.
- UX/UI.

**Hedixon Cardozo — Backend**
Carpetas principales: `/backend`, `/database`

- API REST.
- Lógica de negocio.
- Autenticación.
- Productos, inventario y órdenes.
- Checkout.
- Auditoría.
- PostgreSQL.
- Control transaccional y concurrencia.

**Jhon Ortiz — DevOps / Calidad**
Carpetas principales: `/tests`, `/nginx`, `/.github`, `/docs/despliegue`

- Docker, Docker Compose y Nginx.
- GitHub Actions y CI/CD.
- AWS y deployment.
- Automatización.
- Testing, pruebas de integración y pruebas de concurrencia.
- Rendimiento.
- Seguridad.
- Evidencias técnicas.
- Documentación de despliegue.

> Aunque cada integrante tiene una responsabilidad principal, **el proyecto es colaborativo**: cualquier integrante puede modificar otras áreas cuando sea necesario.

## Estado del proyecto

**Fase 0 — Inicialización del repositorio**

Se creó únicamente la estructura base, la documentación inicial y la configuración básica de Git. No existen funcionalidades, dependencias instaladas, servicios Docker funcionales ni pipelines de CI/CD.

## Estructura del repositorio

```text
TiendaLocal/
├── frontend/
├── backend/
├── database/
├── nginx/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── concurrency/
├── docs/
│   ├── arquitectura/
│   ├── requisitos/
│   ├── pruebas/
│   ├── despliegue/
│   └── decisiones/
├── .github/
│   └── workflows/
├── .gitignore
├── .env.example
├── docker-compose.yml
└── README.md
```

| Ruta | Propósito |
| --- | --- |
| `frontend/` | Aplicación web para compradores y panel administrativo (React + TypeScript + Vite). |
| `backend/` | API REST y lógica de negocio (Python + FastAPI). |
| `database/` | Recursos de PostgreSQL: esquema, migraciones y datos de prueba. |
| `nginx/` | Configuración del reverse proxy. |
| `tests/unit/` | Pruebas unitarias. |
| `tests/integration/` | Pruebas de integración entre componentes. |
| `tests/e2e/` | Pruebas de extremo a extremo. |
| `tests/concurrency/` | Pruebas de concurrencia sobre el inventario. |
| `docs/arquitectura/` | Arquitectura, diagramas, componentes y flujo de datos. |
| `docs/requisitos/` | Requisitos funcionales y no funcionales, criterios de aceptación y trazabilidad. |
| `docs/pruebas/` | Estrategia de testing y resultados. |
| `docs/despliegue/` | Docker, AWS, entornos y CI/CD. |
| `docs/decisiones/` | Decisiones técnicas importantes y sus justificaciones. |
| `.github/workflows/` | Pipelines de GitHub Actions. |
| `.gitignore` | Archivos y carpetas excluidos del control de versiones. |
| `.env.example` | Plantilla de variables de entorno, sin valores reales. |
| `docker-compose.yml` | Orquestación prevista de los servicios (aún no funcional). |

Las carpetas sin contenido incluyen un archivo `.gitkeep` para que Git las conserve.

## Metodología de trabajo

Posteriormente el equipo utilizará:

- Git
- GitHub
- Issues
- Feature branches
- Pull Requests
- Code Review
- GitHub Actions
- Releases

> Estos elementos **aún no están configurados**; se definirán en la siguiente etapa.
