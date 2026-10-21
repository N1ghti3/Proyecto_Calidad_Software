/* =====================================================================
 * Rutas de la aplicación.
 *
 * Antes la tienda era una sola página larga: «Catálogo», «Categorías» y
 * «Artesanos» desplazaban la vista hasta un ancla, de modo que ninguna de
 * esas secciones tenía dirección propia. No se podían compartir, recargar
 * ni abrir en otra pestaña, y el botón «atrás» no las distinguía.
 *
 * Ahora cada sección es una ruta. Este módulo es la única fuente de verdad
 * sobre qué rutas existen: traduce una dirección a la vista que le
 * corresponde y construye las direcciones a partir de los datos. No conoce
 * React, para poder probarlo sin montar nada.
 *
 * nginx resuelve cualquier ruta con `try_files … /index.html`, y Vite hace
 * lo mismo en desarrollo y en `vite preview`, de modo que recargar sobre
 * cualquiera de estas direcciones sirve la aplicación.
 * ===================================================================== */

export const SECCIONES_ADMIN = [
  "inventario", "pedidos", "productos", "auditoria", "notificaciones", "estadisticas",
] as const;
export type SeccionAdmin = (typeof SECCIONES_ADMIN)[number];

export type Ruta =
  | { vista: "home" }
  | { vista: "catalog" }
  | { vista: "categories" }
  | { vista: "category"; slug: string }
  | { vista: "artisans" }
  | { vista: "product"; slug: string }
  | { vista: "favorites" }
  | { vista: "cart" }
  | { vista: "checkout" }
  | { vista: "profile" }
  /** Consulta pública de un pedido (EP-06). El número puede venir en la
   *  dirección; el correo nunca: es un dato personal y las direcciones
   *  quedan en el historial, en los registros del servidor y en el Referer. */
  | { vista: "lookup"; numero: string }
  | { vista: "login"; volver: string | null }
  | { vista: "admin"; seccion: SeccionAdmin; id: string | null; pagina: number }
  | { vista: "notFound" };

/** Direcciones de cada vista. Se usan al construir enlaces, nunca a mano. */
export const rutas = {
  inicio: "/",
  catalogo: "/catalogo",
  categorias: "/categorias",
  categoria: (slug: string) => `/categorias/${encodeURIComponent(slug)}`,
  artesanos: "/artesanos",
  producto: (slug: string) => `/producto/${encodeURIComponent(slug)}`,
  favoritos: "/favoritos",
  carrito: "/carrito",
  pago: "/pago",
  perfil: "/perfil",
  consultar: (numero?: string) =>
    numero ? `/consultar-pedido?numero=${encodeURIComponent(numero)}` : "/consultar-pedido",
  ingresar: (volver?: string) =>
    volver ? `/ingresar?volver=${encodeURIComponent(volver)}` : "/ingresar",
  admin: (seccion: SeccionAdmin = "inventario", opciones: { id?: string; pagina?: number } = {}) => {
    const base = `/admin/${seccion}${opciones.id ? `/${encodeURIComponent(opciones.id)}` : ""}`;
    return opciones.pagina && opciones.pagina > 1 ? `${base}?pagina=${opciones.pagina}` : base;
  },
};

const SLUG = "([a-z0-9-]+)";

/** Traduce una dirección (`pathname` + `search`) a la vista que le corresponde. */
export function leerRuta(direccion: string): Ruta {
  const url = new URL(direccion, "http://local");
  const camino = url.pathname.replace(/\/+$/, "") || "/";
  const q = url.searchParams;
  let m: RegExpMatchArray | null;

  switch (camino) {
    case "/": return { vista: "home" };
    case "/catalogo": return { vista: "catalog" };
    case "/categorias": return { vista: "categories" };
    case "/artesanos": return { vista: "artisans" };
    case "/favoritos": return { vista: "favorites" };
    case "/carrito": return { vista: "cart" };
    case "/pago": return { vista: "checkout" };
    case "/perfil": return { vista: "profile" };
    case "/consultar-pedido": return { vista: "lookup", numero: q.get("numero") ?? "" };
    case "/ingresar": return { vista: "login", volver: volverSeguro(q.get("volver")) };
    case "/admin": return { vista: "admin", seccion: "inventario", id: null, pagina: 1 };
  }

  if ((m = camino.match(new RegExp(`^/categorias/${SLUG}$`)))) return { vista: "category", slug: m[1] };
  if ((m = camino.match(new RegExp(`^/producto/${SLUG}$`)))) return { vista: "product", slug: m[1] };
  if ((m = camino.match(/^\/admin\/([a-z]+)(?:\/([0-9a-f-]{36}|nuevo))?$/))) {
    const seccion = m[1] as SeccionAdmin;
    if (!SECCIONES_ADMIN.includes(seccion)) return { vista: "notFound" };
    // Tienen dirección propia el detalle de un pedido, la edición de un
    // producto y el alta (`/admin/productos/nuevo`).
    if (m[2] && !(seccion === "productos" || (seccion === "pedidos" && m[2] !== "nuevo"))) {
      return { vista: "notFound" };
    }
    const pagina = Math.max(1, Number.parseInt(q.get("pagina") ?? "1", 10) || 1);
    return { vista: "admin", seccion, id: m[2] ?? null, pagina };
  }
  return { vista: "notFound" };
}

/** `volver` solo admite rutas internas del panel. Aceptar cualquier valor
 *  convertiría el inicio de sesión en una redirección abierta: un enlace
 *  `/ingresar?volver=https://sitio-falso` llevaría a la administradora,
 *  recién autenticada, a una copia del panel que pide la contraseña otra vez. */
function volverSeguro(valor: string | null): string | null {
  return valor && /^\/admin(\/[a-z0-9/-]*)?(\?pagina=\d+)?$/.test(valor) ? valor : null;
}

/** Título de la pestaña del navegador para cada vista. */
export function tituloDe(ruta: Ruta, nombres: { categoria?: string; producto?: string } = {}): string {
  const base = "TiendaLocal";
  const titulos: Record<Ruta["vista"], string> = {
    home: "Diseño independiente de Bogotá",
    catalog: "Catálogo",
    categories: "Categorías",
    category: nombres.categoria ?? "Categoría",
    artisans: "Artesanos",
    product: nombres.producto ?? "Producto",
    favorites: "Favoritos",
    cart: "Carrito",
    checkout: "Pago",
    profile: "Mis pedidos",
    lookup: "Consultar pedido",
    login: "Ingresar",
    admin: "Panel",
    notFound: "Página no encontrada",
  };
  if (ruta.vista === "admin") return `${tituloAdmin(ruta.seccion, ruta.id)} · Panel · ${base}`;
  return ruta.vista === "home" ? `${base} — ${titulos.home}` : `${titulos[ruta.vista]} · ${base}`;
}

/** Encabezado de una pantalla del panel; lo comparten la pestaña y el `<h1>`. */
export function tituloAdmin(seccion: SeccionAdmin, id: string | null): string {
  if (!id) return ETIQUETAS_ADMIN[seccion];
  if (seccion === "pedidos") return "Detalle del pedido";
  return id === "nuevo" ? "Nuevo producto" : "Editar producto";
}

export const ETIQUETAS_ADMIN: Record<SeccionAdmin, string> = {
  inventario: "Inventario",
  pedidos: "Pedidos",
  productos: "Productos",
  auditoria: "Auditoría",
  notificaciones: "Notificaciones",
  estadisticas: "Estadísticas",
};
