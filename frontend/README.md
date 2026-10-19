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

Vite redirige `/api` al backend (`http://localhost:8000` por defecto). Para
apuntar a otro servidor:

```bash
API_URL=http://localhost:8001 npm run dev
```

### Mientras el backend no esté listo

`mock-api.mjs` implementa el contrato con datos en memoria. **No es el backend
del proyecto** —el backend real es FastAPI y vive en [`../backend/`](../backend/)—
sino una herramienta para desarrollar y probar la interfaz sin depender de que
la API esté terminada.

```bash
node mock-api.mjs        # http://localhost:8000/api/v1
npm run dev              # en otra terminal
```

Credenciales del panel en el servidor de apoyo:
`admin@tiendalocal.co` / `tiendalocal2026`

Sirve además como **referencia ejecutable del contrato**: si el frontend
funciona contra él, funcionará contra FastAPI siempre que este respete los
mismos nombres, formatos y códigos de error.

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
