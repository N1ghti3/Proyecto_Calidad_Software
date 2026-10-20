# Frontend — TiendaLocal

Aplicación web del comprador y panel de administración.
**React 19 · TypeScript 5.7 · Vite 7 · Tailwind CSS 4**

Consume el contrato documentado en [`../docs/api/`](../docs/api/): base `/api/v1`,
identificadores UUID, JSON en camelCase y colecciones envueltas en `Page<T>`.

---

## Puesta en marcha

```bash
npm ci
npm run dev        # http://localhost:5173
```

Vite redirige `/api` al backend (`http://127.0.0.1:8000` por defecto). Para
apuntar a otro servidor:

```bash
API_URL=http://127.0.0.1:8001 npm run dev
```

El backend real es FastAPI y vive en [`../backend/`](../backend/). Para
levantarlo, sigue el README de la raíz: la base de datos con Docker, las
migraciones de Alembic y la siembra de desarrollo.

Credenciales del panel que crea la siembra: `admin@example.com`, con la
contraseña que hayas puesto en `ADMIN_SEED_PASSWORD` dentro de `.env`.

### Mientras el backend no esté disponible

`mock-api.mjs` implementa el mismo contrato con datos en memoria. **No es el
backend del proyecto**: permite desarrollar la interfaz sin depender de que la
API esté corriendo, y sirve de **referencia ejecutable del contrato**.

```bash
node mock-api.mjs        # http://localhost:8000/api/v1
npm run dev              # en otra terminal
```

Sus credenciales son `admin@tiendalocal.co` / `tiendalocal2026`, distintas a
propósito de las del backend real para que nunca se confunda uno con otro.

---

## Compilación

```bash
npm run build      # tsc --noEmit && vite build  →  dist/
npm run preview    # revisa el build localmente
```

El script de build ejecuta primero la verificación de tipos: si el frontend deja
de coincidir con los tipos del contrato, **la compilación falla** en lugar de
producir un paquete que se rompería en ejecución.

Peso del último build: **≈ 90 KB con gzip** (JS + CSS + HTML), frente al
presupuesto de 1,5 MB de RNF-01.

---

## Estructura

| Archivo | Contenido |
|---|---|
| `src/api.ts` | Única capa que conoce rutas y formatos del backend. Tipos del contrato, manejo de errores y sesión del panel |
| `src/App.tsx` | Vistas y estado de la aplicación |
| `src/index.css` | Estilos del diseño |
| `mock-api.mjs` | Servidor de apoyo para desarrollo (no es el backend) |

---

## Endpoints que consume

| Endpoint | Uso en la interfaz |
|---|---|
| `GET /products` | Catálogo. Recorre las páginas hasta completar (límite de 50 por página) |
| `GET /products/{slug}` | Detalle. **Necesario para comprar**: el resumen no trae los `variantId` |
| `GET /categories` | Navegación y conteos |
| `POST /cart/validate` | Comprobación informativa de disponibilidad |
| `POST /orders` | Confirmación del pedido |
| `POST /auth/login` | Acceso al panel; el token queda en memoria |
| `GET /admin/inventory` | Inventario por variante |
| `GET /admin/orders` | Pedidos y ventas |
| `PATCH /admin/variants/{id}/inventory` | Ajuste de existencias |

---

## Decisiones de interfaz y su razón

**Se compra por variante, nunca por producto (RN-05).** El carrito guarda
`variantId`, no el identificador del producto. Agregar desde una tarjeta del
catálogo obliga a pedir el detalle, porque el resumen solo trae los nombres de
las tallas y no sus identificadores.

**La disponibilidad no depende del color.** Cada variante agotada se comunica
por tres vías: control deshabilitado, texto tachado y etiqueta con las unidades
restantes. Responde al criterio de WCAG 2.2 sobre no usar el color como único
medio.

**El consentimiento es obligatorio en el formulario (RN-16).** La casilla es
`required`, y si aun así llegara sin marcar, el backend responde
`CONSENT_REQUIRED` y la interfaz lo muestra junto a la casilla.

**`INSUFFICIENT_STOCK` se muestra línea por línea.** Cuando alguien compra las
últimas unidades mientras el comprador llena el formulario, se indica por
producto y talla cuánto pidió y cuánto queda, en lugar de un error genérico.

**El aviso de confirmación vive en el estado de la aplicación, no en la vista.**
Si viviera en el componente del checkout, recargar el catálogo tras el descuento
lo desmontaría y el comprador nunca vería el número de su pedido.

---

## Pendientes

- **Galería:** el detalle muestra la primera imagen; faltan las miniaturas
  cuando el producto trae varias (`images[]`).
- **Favoritos:** se guardan en memoria y se pierden al recargar.
- **Registro de clientes:** el formulario existe en la interfaz, pero el
  contrato no define todavía un endpoint de registro público.
- **Filtros del catálogo:** la API admite `q`, `category`, `size`, `inStock` y
  `sort`; la interfaz solo usa la búsqueda por nombre.
