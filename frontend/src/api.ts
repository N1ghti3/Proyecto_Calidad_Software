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
  /** Total de las líneas satisfacibles; el carrito lo muestra tal cual. */
  totalCop: number;
  checkedAt: string;
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
  lineTotalCop: number;
};

export type EstadoOrden = "CONFIRMADA" | "PREPARADA" | "ENTREGADA" | "CANCELADA";

export type OrderResponse = {
  id: string;
  orderNumber: string;
  status: EstadoOrden;
  items: OrderItemResponse[];
  totalCop: number;
  /** En la consulta pública (EP-06) llega enmascarado: `a***@correo.com`. */
  customer: CustomerRequest;
  simulatedCheckout?: boolean;
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
  /** Mismo nombre que recibe el ajuste (EP-15): el panel lee y escribe un campo. */
  stockQuantity: number;
  updatedAt?: string | null;
  priceCop?: number;
  categoryName?: string;
  imageUrl?: string | null;
  published?: boolean;
  lowStock?: boolean;
};

export type AdminUserResponse = { id: string; email: string; fullName: string };

export type LoginResponse = {
  accessToken: string;
  tokenType: string;
  expiresIn: number;
  user: AdminUserResponse;
};

export type AdminProductSummaryResponse = ProductSummaryResponse & { published: boolean };

export type AuditEntryResponse = {
  id: string;
  entityType: "INVENTORY" | "ORDER" | "PRODUCT";
  entityId: string;
  action: "STOCK_CHANGE" | "STATUS_CHANGE" | "PUBLISH_CHANGE";
  source: "AJUSTE_MANUAL" | "ORDEN" | "CANCELACION";
  oldValue: string | null;
  newValue: string;
  /** Nombre del administrador; null cuando el cambio lo originó una compra. */
  performedBy: string | null;
  reason: string | null;
  createdAt: string;
};

export type NotificationResponse = {
  id: string;
  orderId: string;
  recipientType: "COMPRADOR" | "ADMINISTRADOR";
  recipient: string;
  status: "PENDIENTE" | "ENVIADA" | "FALLIDA";
  attempts: number;
  createdAt: string;
};

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

/* El token vive solo en memoria, a propósito: guardado en localStorage
   quedaría al alcance de cualquier script inyectado (XSS). El costo es que
   recargar la página cierra la sesión; las rutas del panel lo resuelven
   llevando al inicio de sesión y devolviendo después a la misma sección. */
let tokenAdmin: string | null = null;
let usuarioAdmin: AdminUserResponse | null = null;
export const fijarToken = (t: string | null, usuario: AdminUserResponse | null = null) => {
  tokenAdmin = t; usuarioAdmin = t ? usuario : null;
};
export const haySesion = () => tokenAdmin !== null;
export const usuarioActual = () => usuarioAdmin;

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

/** Recorre todas las páginas de una colección. El contrato limita pageSize
 *  a 50; se piden en serie para no saturar al servidor. */
async function recorrer<T>(pagina: (n: number) => Promise<Page<T>>): Promise<T[]> {
  const primera = await pagina(1);
  const todos = [...primera.items];
  for (let n = 2; n <= primera.meta.totalPages; n += 1) todos.push(...(await pagina(n)).items);
  return todos;
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
export const listarCatalogoCompleto = (filtros: Parameters<typeof listarProductos>[0] = {}) =>
  recorrer(page => listarProductos({ ...filtros, page, pageSize: 50 }));

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
  fijarToken(r.accessToken, r.user);
  return r;
}

export const cerrarSesion = () => fijarToken(null);

/** EP-24 · GET /admin/inventory — todas las variantes activas. */
export const obtenerInventario = () =>
  recorrer(page => pedir<Page<InventoryResponse>>(
    `/admin/inventory${consulta({ page, pageSize: 50, lowStockThreshold: 5 })}`, { auth: true }));

/** EP-15 · PATCH /admin/variants/{id}/inventory — fija el valor final; el motivo
 *  es obligatorio porque queda en la auditoría (RN-25). */
export const ajustarInventario = (variantId: string, stockQuantity: number, reason: string) =>
  pedir<InventoryResponse>(`/admin/variants/${variantId}/inventory`, {
    method: "PATCH",
    auth: true,
    body: JSON.stringify({ stockQuantity, reason }),
  });

/** EP-17 · GET /admin/orders — una página. */
export const obtenerOrdenesAdmin = (page = 1, pageSize = 20) =>
  pedir<Page<OrderSummaryResponse>>(`/admin/orders${consulta({ page, pageSize })}`, { auth: true });

/** EP-17 recorrido completo, para las estadísticas. */
export const obtenerTodasLasOrdenes = () => recorrer(page => obtenerOrdenesAdmin(page, 50));

/** EP-23 · GET /admin/orders/{id} — sin enmascarar, para despachar. */
export const obtenerOrdenAdmin = (id: string) =>
  pedir<OrderResponse>(`/admin/orders/${encodeURIComponent(id)}`, { auth: true });

/** EP-18 · PATCH /admin/orders/{id}/status — cancelar exige motivo. */
export const cambiarEstadoOrden = (id: string, status: EstadoOrden, reason?: string) =>
  pedir<OrderResponse>(`/admin/orders/${encodeURIComponent(id)}/status`, {
    method: "PATCH",
    auth: true,
    body: JSON.stringify({ status, ...(reason ? { reason } : {}) }),
  });

/** EP-21 · GET /admin/products — incluye los despublicados. */
export const listarProductosAdmin = () =>
  recorrer(page => pedir<Page<AdminProductSummaryResponse>>(
    `/admin/products${consulta({ page, pageSize: 50, sort: "name:asc" })}`, { auth: true }));

/** EP-13 · PATCH /admin/products/{id}/publish */
export const publicarProducto = (id: string, published: boolean) =>
  pedir<AdminProductSummaryResponse>(`/admin/products/${encodeURIComponent(id)}/publish`, {
    method: "PATCH",
    auth: true,
    body: JSON.stringify({ published }),
  });

/** EP-19 · GET /admin/audit-logs — solo lectura (RN-25). */
export const obtenerAuditoria = (page = 1) =>
  pedir<Page<AuditEntryResponse>>(`/admin/audit-logs${consulta({ page, pageSize: 20 })}`, { auth: true });

/** EP-20 · GET /admin/notifications */
export const obtenerNotificaciones = (page = 1) =>
  pedir<Page<NotificationResponse>>(`/admin/notifications${consulta({ page, pageSize: 20 })}`, { auth: true });

/** Transiciones permitidas (RN-13). El servidor las vuelve a validar; aquí
 *  solo sirven para no ofrecer botones que de antemano se sabe que fallan. */
export const TRANSICIONES: Record<EstadoOrden, EstadoOrden[]> = {
  CONFIRMADA: ["PREPARADA", "CANCELADA"],
  PREPARADA: ["ENTREGADA", "CANCELADA"],
  ENTREGADA: [],
  CANCELADA: [],
};

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

/** Fecha y hora en Bogotá, para la auditoría y las notificaciones. */
export const fechaHoraLocal = (iso: string) =>
  new Date(iso).toLocaleString("es-CO", {
    day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
    timeZone: "America/Bogota",
  });
