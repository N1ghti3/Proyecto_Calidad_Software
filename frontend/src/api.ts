/* =====================================================================
 * Capa de acceso a la API de TiendaLocal.
 *
 * Implementa el contrato documentado del equipo:
 *   docs/api/endpoints.md · modelos.md · convenciones.md · errores.md
 *
 * Reglas del contrato que este archivo respeta:
 *   · Base versionada en la ruta: /api/v1 (ADR-004)
 *   · Identificadores UUID en cadena; el detalle público se pide por slug
 *   · JSON en camelCase (ADR-003); ninguna conversión ad hoc fuera de aquí
 *   · Colecciones envueltas en Page<T> con meta de paginación
 *   · Errores con la forma { error: { code, message, details, requestId } }
 *
 * Es el único punto del frontend que conoce rutas y formatos del backend.
 * ===================================================================== */

const BASE = import.meta.env.VITE_API_URL ?? "/api/v1";

/* ------------------------------------------------------------ modelos */

export type CategoryResponse = {
  id: string;
  name: string;
  slug: string;
  productCount: number;
};

export type ProductSummaryResponse = {
  id: string;
  slug: string;
  name: string;
  priceCop: number;
  categoryName: string;
  imageUrl: string | null;
  imageAlt: string | null;
  availableUnits: number;
  inStock: boolean;
  sizes: string[];
};

export type ProductVariantResponse = {
  id: string;
  sku: string;
  size: string;
  availableUnits: number;
  inStock: boolean;
};

export type ProductImageResponse = {
  id: string;
  url: string;
  alt: string | null;
  position?: number;
};

export type ProductResponse = ProductSummaryResponse & {
  description: string | null;
  category: CategoryResponse;
  images: ProductImageResponse[];
  variants: ProductVariantResponse[];
};

export type PageMeta = { page: number; pageSize: number; totalItems: number; totalPages: number };
export type Page<T> = { items: T[]; meta: PageMeta };

export type CartItemRequest = { variantId: string; quantity: number };

export type CartValidationResponse = {
  valid: boolean;
  items: {
    variantId: string;
    productName: string;
    size: string;
    requestedQuantity: number;
    availableUnits: number;
    available: boolean;
    unitPriceCop: number;
  }[];
};

export type CustomerRequest = {
  name: string;
  email: string;
  phone: string;
  address: string;
  city: string;
};

export type OrderItemResponse = {
  variantId: string;
  productName: string;
  size: string;
  quantity: number;
  unitPriceCop: number;
  subtotalCop?: number;
};

export type OrderResponse = {
  id: string;
  orderNumber: string;
  status: "CONFIRMADA" | "PREPARADA" | "ENTREGADA" | "CANCELADA";
  items: OrderItemResponse[];
  totalCop: number;
  customer: CustomerRequest;
  createdAt?: string;
};

export type OrderSummaryResponse = {
  id: string;
  orderNumber: string;
  status: OrderResponse["status"];
  totalCop: number;
  createdAt: string;
  customerName?: string;
  itemCount?: number;
};

export type InventoryResponse = {
  variantId: string;
  productId: string;
  productName: string;
  sku: string;
  size: string;
  availableUnits: number;
  priceCop?: number;
  categoryName?: string;
  imageUrl?: string | null;
  published?: boolean;
};

export type LoginResponse = { accessToken: string; tokenType?: string; expiresIn?: number };

/* ------------------------------------------------------------- errores */

/** Detalle de una línea con existencias insuficientes (errores.md). */
export type StockDetalle = {
  variantId: string;
  productName: string;
  size: string;
  requestedQuantity: number;
  availableUnits: number;
};

/** Error de la API con el código estable del contrato. */
export class ApiError extends Error {
  code: string;
  status: number;
  details: Record<string, unknown>;
  requestId: string;
  constructor(code: string, message: string, status: number,
              details: Record<string, unknown> = {}, requestId = "") {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
    this.requestId = requestId;
  }
  /** Líneas problemáticas cuando el código es INSUFFICIENT_STOCK. */
  get lineasSinStock(): StockDetalle[] {
    return (this.details.items as StockDetalle[]) ?? [];
  }
}

/* ------------------------------------------------------------- sesión */

let tokenAdmin: string | null = null;
export const fijarToken = (t: string | null) => { tokenAdmin = t; };
export const haySesion = () => tokenAdmin !== null;

/* --------------------------------------------------------- transporte */

async function pedir<T>(ruta: string, opciones: RequestInit & { auth?: boolean } = {}): Promise<T> {
  const { auth, headers, ...resto } = opciones;
  const cabeceras: Record<string, string> = {
    "Content-Type": "application/json; charset=utf-8",
    ...(headers as Record<string, string>),
  };
  if (auth && tokenAdmin) cabeceras.Authorization = `Bearer ${tokenAdmin}`;

  let respuesta: Response;
  try {
    respuesta = await fetch(BASE + ruta, { headers: cabeceras, ...resto });
  } catch {
    throw new ApiError("NETWORK_ERROR",
      "No se pudo conectar con el servidor. Verifica que la API esté activa.", 0);
  }

  if (respuesta.status === 204) return undefined as T;

  const cuerpo = await respuesta.json().catch(() => null);

  if (!respuesta.ok) {
    const e = cuerpo?.error ?? {};
    throw new ApiError(
      e.code ?? "INTERNAL_ERROR",
      e.message ?? `Error ${respuesta.status}`,
      respuesta.status,
      e.details ?? {},
      e.requestId ?? respuesta.headers.get("X-Request-Id") ?? "",
    );
  }
  return cuerpo as T;
}

const consulta = (params: Record<string, string | number | boolean | undefined>) => {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
};

/* ------------------------------------------------------------ públicos */

/** EP-01 · GET /products — listado paginado del catálogo. */
export const listarProductos = (filtros: {
  q?: string; category?: string; size?: string; inStock?: boolean;
  sort?: string; page?: number; pageSize?: number;
} = {}) =>
  pedir<Page<ProductSummaryResponse>>(`/products${consulta(filtros)}`);

/**
 * Trae el catálogo completo recorriendo las páginas.
 * El contrato limita pageSize a 50, así que un catálogo mayor exige
 * varias peticiones; se hacen en serie para no saturar al servidor.
 */
export async function listarCatalogoCompleto(
  filtros: Parameters<typeof listarProductos>[0] = {},
): Promise<ProductSummaryResponse[]> {
  const primera = await listarProductos({ ...filtros, page: 1, pageSize: 50 });
  const todos = [...primera.items];
  for (let p = 2; p <= primera.meta.totalPages; p += 1) {
    const siguiente = await listarProductos({ ...filtros, page: p, pageSize: 50 });
    todos.push(...siguiente.items);
  }
  return todos;
}

/** EP-02 · GET /categories */
export const listarCategorias = () => pedir<CategoryResponse[]>("/categories");

/** EP-03 · GET /products/{slug} — detalle con variantes comprables. */
export const obtenerProducto = (slug: string) =>
  pedir<ProductResponse>(`/products/${encodeURIComponent(slug)}`);

/** EP-04 · POST /cart/validate — informativo, no reserva unidades (RN-06). */
export const validarCarrito = (items: CartItemRequest[]) =>
  pedir<CartValidationResponse>("/cart/validate", {
    method: "POST",
    body: JSON.stringify({ items }),
  });

/** EP-05 · POST /orders — valida, descuenta y confirma en una transacción. */
export const crearOrden = (
  items: CartItemRequest[],
  customer: CustomerRequest,
  dataProcessingConsent: boolean,
  privacyNoticeVersion = AVISO_PRIVACIDAD,
) =>
  pedir<OrderResponse>("/orders", {
    method: "POST",
    body: JSON.stringify({ items, customer, dataProcessingConsent, privacyNoticeVersion }),
  });

/** EP-06 · GET /orders/{orderNumber} — requiere el correo del comprador (RN-18). */
export const consultarOrden = (orderNumber: string, email: string) =>
  pedir<OrderResponse>(`/orders/${encodeURIComponent(orderNumber)}${consulta({ email })}`);

/* -------------------------------------------------------- administración */

/** EP-10 · POST /auth/login */
export async function iniciarSesion(email: string, password: string) {
  const r = await pedir<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  fijarToken(r.accessToken);
  return r;
}

export const cerrarSesion = () => fijarToken(null);

/** EP-24 · GET /admin/inventory */
export const obtenerInventario = () =>
  pedir<Page<InventoryResponse>>(`/admin/inventory${consulta({ pageSize: 50 })}`, { auth: true });

/** EP-17 · GET /admin/orders */
export const obtenerOrdenesAdmin = () =>
  pedir<Page<OrderSummaryResponse>>(`/admin/orders${consulta({ pageSize: 50 })}`, { auth: true });

/** EP-15 · PATCH /admin/variants/{id}/inventory */
export const ajustarInventario = (variantId: string, availableUnits: number, reason?: string) =>
  pedir<InventoryResponse>(`/admin/variants/${variantId}/inventory`, {
    method: "PATCH",
    auth: true,
    body: JSON.stringify({ availableUnits, ...(reason ? { reason } : {}) }),
  });

/* ----------------------------------------------------------- utilidades */

/** Versión del aviso de privacidad que se muestra al comprador (RN-16). */
export const AVISO_PRIVACIDAD = "1.0";

/** Formatea un entero de pesos como "$189.000". */
export const cop = (valor: number) => "$" + valor.toLocaleString("es-CO");

/** Fecha en hora local de Bogotá; la API siempre envía UTC (convenciones.md). */
export const fechaLocal = (iso: string) =>
  new Date(iso).toLocaleDateString("es-CO", {
    day: "2-digit", month: "long", year: "numeric", timeZone: "America/Bogota",
  });
