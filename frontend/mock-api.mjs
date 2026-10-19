/* =====================================================================
 * Servidor de apoyo para desarrollo del frontend.
 *
 * NO es el backend del proyecto. El backend real es FastAPI y vive en
 * backend/. Este archivo implementa el contrato documentado en
 * docs/api/ (EP-01 a EP-05, EP-10, EP-15, EP-17, EP-24) con datos en
 * memoria, para poder desarrollar y probar la interfaz mientras la API
 * se termina.
 *
 * Sirve además como referencia ejecutable del contrato: si el frontend
 * funciona contra este servidor, funcionará contra FastAPI siempre que
 * este respete los mismos nombres, formatos y códigos de error.
 *
 *   node mock-api.mjs        →  http://localhost:8000/api/v1
 * ===================================================================== */

import { createServer } from "node:http";
import { randomUUID } from "node:crypto";

const PUERTO = Number(process.env.MOCK_PORT || 8000);
const AVISO = "1.0";

/* ----------------------------------------------------------- datos */

const categorias = [
  { id: randomUUID(), name: "Chaquetas",    slug: "chaquetas" },
  { id: randomUUID(), name: "Camisetas",    slug: "camisetas" },
  { id: randomUUID(), name: "Bolsos",       slug: "bolsos" },
  { id: randomUUID(), name: "Joyería",      slug: "joyeria" },
  { id: randomUUID(), name: "Calzado",      slug: "calzado" },
  { id: randomUUID(), name: "Hogar & arte", slug: "hogar-y-arte" },
];

const IMG = {
  chaqueta: "https://images.unsplash.com/photo-1767036840968-91dc63654cd7?auto=format&fit=crop&w=900&q=85",
  camiseta: "https://images.unsplash.com/photo-1618718123715-a2db2f17e908?auto=format&fit=crop&w=900&q=85",
  bolso:    "https://images.unsplash.com/photo-1741188491649-7df9303dd892?auto=format&fit=crop&w=900&q=85",
  joya:     "https://images.unsplash.com/photo-1567736464933-bc179b82a448?auto=format&fit=crop&w=900&q=85",
  calzado:  "https://images.unsplash.com/photo-1634801634476-2d98226094fe?auto=format&fit=crop&w=900&q=85",
  hogar:    "https://images.unsplash.com/photo-1534413340928-7bd74b65196f?auto=format&fit=crop&w=900&q=85",
};

const slugificar = (s) =>
  s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "")
   .replace(/&/g, "y").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

function producto(nombre, catSlug, precio, descripcion, imagen, tallas) {
  const cat = categorias.find(c => c.slug === catSlug);
  const slug = slugificar(nombre);
  const variants = tallas.map(([size, units]) => ({
    id: randomUUID(),
    sku: `${slug.slice(0, 3).toUpperCase()}-${size}`,
    size,
    availableUnits: units,
    get inStock() { return this.availableUnits > 0; },
  }));
  return {
    id: randomUUID(), slug, name: nombre, description: descripcion,
    priceCop: precio, category: cat,
    images: [{ id: randomUUID(), url: imagen, alt: `${nombre}, pieza de ${cat.name.toLowerCase()}`, position: 1 }],
    variants, published: true,
  };
}

const productos = [
  producto("Chaqueta Niebla", "chaquetas", 189000, "Silueta amplia y liviana, hecha en Bogotá con textil recuperado.", IMG.chaqueta, [["XS",3],["S",5],["M",7],["L",4],["XL",2]]),
  producto("Chaqueta Andina", "chaquetas", 198000, "Capa urbana de corte recto para el clima de la sabana.", IMG.chaqueta, [["S",4],["M",6],["L",3]]),
  producto("Sobrecamisa Monserrate", "chaquetas", 174000, "Sobrecamisa en denim suave, ideal como segunda capa.", IMG.chaqueta, [["M",5],["L",4],["XL",2]]),
  producto("Bomber Séptima", "chaquetas", 229000, "Edición limitada en tejido técnico con forro acolchado.", IMG.chaqueta, [["S",2],["M",3],["L",1]]),
  producto("Camiseta Horizonte", "camisetas", 98000, "Algodón orgánico con serigrafía hecha a mano.", IMG.camiseta, [["S",10],["M",14],["L",9]]),
  producto("Camiseta Origen", "camisetas", 82000, "Básico de corte holgado en algodón peinado.", IMG.camiseta, [["S",12],["M",15],["L",11],["XL",6]]),
  producto("Camiseta Calle 85", "camisetas", 89000, "Gráfica inspirada en la arquitectura del barrio.", IMG.camiseta, [["M",8],["L",7]]),
  producto("Buzo Altiplano", "camisetas", 149000, "Felpa perchada, abrigado y de caída relajada.", IMG.camiseta, [["S",5],["M",6],["L",4]]),
  producto("Bolso Tejido Muisca", "bolsos", 126000, "Tejido tradicional en fique por artesanas de Boyacá.", IMG.bolso, [["Única",6]]),
  producto("Bolso Trama", "bolsos", 139000, "Trama en algodón natural con asas de cuero vegetal.", IMG.bolso, [["Única",8]]),
  producto("Bandolera Centro", "bolsos", 118000, "Bandolera compacta con bolsillo interior.", IMG.bolso, [["Única",5]]),
  producto("Mochila Telar", "bolsos", 156000, "Pieza única tejida en telar vertical.", IMG.bolso, [["Única",2]]),
  producto("Aretes Sol", "joyeria", 74000, "Latón martillado a mano con baño de oro.", IMG.joya, [["Única",18]]),
  producto("Aretes Guatavita", "joyeria", 68000, "Acabado mate en plata ley 925.", IMG.joya, [["Única",14]]),
  producto("Collar Dorado", "joyeria", 112000, "Cadena fina con dije de tagua tallada.", IMG.joya, [["Única",9]]),
  producto("Anillo Páramo", "joyeria", 59000, "Anillo ajustable con textura de frailejón.", IMG.joya, [["Única",20]]),
  producto("Tenis Distrito", "calzado", 219000, "Suela de caucho reciclado y lona orgánica.", IMG.calzado, [["36",3],["37",4],["38",5],["39",4],["40",3]]),
  producto("Botín Sabana", "calzado", 279000, "Cuero curtido vegetalmente, costura reforzada.", IMG.calzado, [["37",2],["38",3],["39",3],["40",2]]),
  producto("Mocasín Nogal", "calzado", 238000, "Horma cómoda para caminar la ciudad.", IMG.calzado, [["38",4],["39",5],["40",3]]),
  producto("Sandalia Macarena", "calzado", 159000, "Tiras trenzadas sobre plantilla de corcho.", IMG.calzado, [["36",6],["37",7],["38",5]]),
  producto("Canasto Palma", "hogar-y-arte", 89000, "Fibra de palma de iraca tejida en Usiacurí.", IMG.hogar, [["Única",11]]),
  producto("Cojín Telar", "hogar-y-arte", 76000, "Funda tejida en telar con relleno reciclado.", IMG.hogar, [["Única",13]]),
  producto("Cuenco Barro", "hogar-y-arte", 54000, "Barro cocido a leña y esmaltado a mano.", IMG.hogar, [["Única",16]]),
  producto("Tapiz Cordillera", "hogar-y-arte", 168000, "Lana virgen teñida con tintes naturales.", IMG.hogar, [["Única",4]]),
];

const borrador = producto("Gorra bordada", "camisetas", 55000, "En preparación.", IMG.camiseta, [["Única",12]]);
borrador.published = false;
productos.push(borrador);

const ordenes = [];
let secuencia = 0;

/* ------------------------------------------------------- utilidades */

const unidades = (p) => p.variants.reduce((s, v) => s + v.availableUnits, 0);

const resumen = (p) => ({
  id: p.id, slug: p.slug, name: p.name, priceCop: p.priceCop,
  categoryName: p.category.name,
  imageUrl: p.images[0]?.url ?? null,
  imageAlt: p.images[0]?.alt ?? null,
  availableUnits: unidades(p),
  inStock: unidades(p) > 0,
  sizes: p.variants.map(v => v.size),
});

const detalle = (p) => ({
  ...resumen(p),
  description: p.description,
  category: { ...p.category, productCount: productos.filter(x => x.published && x.category.id === p.category.id).length },
  images: p.images,
  variants: p.variants.map(v => ({
    id: v.id, sku: v.sku, size: v.size,
    availableUnits: v.availableUnits, inStock: v.availableUnits > 0,
  })),
});

const numeroOrden = () => {
  secuencia += 1;
  const f = new Date();
  const ymd = `${f.getUTCFullYear()}${String(f.getUTCMonth() + 1).padStart(2, "0")}${String(f.getUTCDate()).padStart(2, "0")}`;
  return `TL-${ymd}-${String(secuencia).padStart(5, "0")}`;
};

function enviar(res, status, cuerpo) {
  const texto = cuerpo === undefined ? "" : JSON.stringify(cuerpo);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "X-Request-Id": `req_${randomUUID().slice(0, 12)}`,
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Methods": "GET, POST, PATCH, OPTIONS",
  });
  res.end(texto);
}

const fallo = (res, status, code, message, details = {}) =>
  enviar(res, status, { error: { code, message, details, requestId: `req_${randomUUID().slice(0, 12)}` } });

const pagina = (items, url) => {
  const page = Math.max(1, Number(url.searchParams.get("page") || 1));
  const pageSize = Math.min(50, Math.max(1, Number(url.searchParams.get("pageSize") || 12)));
  const inicio = (page - 1) * pageSize;
  return {
    items: items.slice(inicio, inicio + pageSize),
    meta: { page, pageSize, totalItems: items.length, totalPages: Math.max(1, Math.ceil(items.length / pageSize)) },
  };
};

const leerCuerpo = (req) => new Promise((resolve, reject) => {
  let datos = "";
  req.on("data", c => { datos += c; if (datos.length > 1e6) req.destroy(); });
  req.on("end", () => { try { resolve(datos ? JSON.parse(datos) : {}); } catch { reject(new Error("JSON inválido")); } });
});

const autenticado = (req) => (req.headers.authorization || "").startsWith("Bearer ");

/* --------------------------------------------------------- rutas */

const servidor = createServer(async (req, res) => {
  if (req.method === "OPTIONS") return enviar(res, 204);

  const url = new URL(req.url, `http://${req.headers.host}`);
  const ruta = url.pathname.replace(/^\/api\/v1/, "");
  const m = (metodo, patron) => req.method === metodo && patron.test(ruta);

  try {
    // EP-02 · GET /categories
    if (m("GET", /^\/categories$/)) {
      return enviar(res, 200, categorias.map(c => ({
        ...c, productCount: productos.filter(p => p.published && p.category.id === c.id).length,
      })));
    }

    // EP-01 · GET /products
    if (m("GET", /^\/products$/)) {
      let lista = productos.filter(p => p.published);
      const q = url.searchParams.get("q");
      const cat = url.searchParams.getAll("category");
      const size = url.searchParams.getAll("size");
      const inStock = url.searchParams.get("inStock");

      if (q) {
        if (q.length < 2 || q.length > 80) {
          return fallo(res, 400, "VALIDATION_ERROR", "Parámetro q fuera de rango",
            { fields: [{ field: "q", issue: "debe tener entre 2 y 80 caracteres" }] });
        }
        const norm = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
        lista = lista.filter(p => norm(p.name).includes(norm(q)));
      }
      if (cat.length) lista = lista.filter(p => cat.includes(p.category.slug));
      if (size.length) {
        const todas = new Set(productos.flatMap(p => p.variants.map(v => v.size)));
        const desconocida = size.find(s => !todas.has(s));
        if (desconocida) {
          return fallo(res, 400, "VALIDATION_ERROR", "Talla inexistente en el catálogo",
            { fields: [{ field: "size", issue: `la talla ${desconocida} no existe` }] });
        }
        lista = lista.filter(p => p.variants.some(v => size.includes(v.size)));
      }
      if (inStock === "true") lista = lista.filter(p => unidades(p) > 0);

      return enviar(res, 200, pagina(lista.map(resumen), url));
    }

    // EP-03 · GET /products/{slug}
    if (m("GET", /^\/products\/[^/]+$/)) {
      const slug = decodeURIComponent(ruta.split("/")[2]);
      const p = productos.find(x => x.slug === slug && x.published);
      if (!p) return fallo(res, 404, "NOT_FOUND", "El producto no existe o no está disponible");
      return enviar(res, 200, detalle(p));
    }

    // EP-04 · POST /cart/validate
    if (m("POST", /^\/cart\/validate$/)) {
      const { items = [] } = await leerCuerpo(req);
      if (!Array.isArray(items) || items.length === 0 || items.length > 50) {
        return fallo(res, 400, "VALIDATION_ERROR", "El carrito debe tener entre 1 y 50 líneas",
          { fields: [{ field: "items", issue: "cantidad fuera de rango" }] });
      }
      const detalles = items.map(it => {
        const p = productos.find(x => x.variants.some(v => v.id === it.variantId));
        const v = p?.variants.find(v => v.id === it.variantId);
        return {
          variantId: it.variantId,
          productName: p?.name ?? "Producto no encontrado",
          size: v?.size ?? "—",
          requestedQuantity: it.quantity,
          availableUnits: v?.availableUnits ?? 0,
          available: (v?.availableUnits ?? 0) >= it.quantity,
          unitPriceCop: p?.priceCop ?? 0,
        };
      });
      return enviar(res, 200, { valid: detalles.every(d => d.available), items: detalles });
    }

    // EP-05 · POST /orders
    if (m("POST", /^\/orders$/)) {
      const cuerpo = await leerCuerpo(req);
      const { items = [], customer = {}, dataProcessingConsent, privacyNoticeVersion } = cuerpo;

      if (dataProcessingConsent !== true) {
        return fallo(res, 400, "CONSENT_REQUIRED",
          "Falta la autorización de tratamiento de datos", { field: "dataProcessingConsent" });
      }
      const campos = [];
      if (!customer.name || customer.name.length < 3) campos.push({ field: "customer.name", issue: "entre 3 y 120 caracteres" });
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(customer.email || "")) campos.push({ field: "customer.email", issue: "formato inválido" });
      if (!/^\+?[0-9]{7,15}$/.test(customer.phone || "")) campos.push({ field: "customer.phone", issue: "entre 7 y 15 dígitos" });
      if (!customer.address || customer.address.length < 5) campos.push({ field: "customer.address", issue: "entre 5 y 200 caracteres" });
      if (!customer.city || customer.city.length < 2) campos.push({ field: "customer.city", issue: "entre 2 y 80 caracteres" });
      if (!privacyNoticeVersion) campos.push({ field: "privacyNoticeVersion", issue: "requerido" });
      if (!Array.isArray(items) || !items.length) campos.push({ field: "items", issue: "al menos una línea" });
      if (campos.length) return fallo(res, 400, "VALIDATION_ERROR", "La petición no cumple el esquema", { fields: campos });

      // Verificación de existencias (RN-07, RN-11)
      const problemas = [];
      for (const it of items) {
        const p = productos.find(x => x.variants.some(v => v.id === it.variantId));
        const v = p?.variants.find(v => v.id === it.variantId);
        if (!p || !v) { problemas.push({ variantId: it.variantId, productName: "Desconocido", size: "—", requestedQuantity: it.quantity, availableUnits: 0 }); continue; }
        if (v.availableUnits < it.quantity) {
          problemas.push({ variantId: v.id, productName: p.name, size: v.size, requestedQuantity: it.quantity, availableUnits: v.availableUnits });
        }
      }
      if (problemas.length) {
        return fallo(res, 409, "INSUFFICIENT_STOCK",
          "Algunos productos ya no tienen unidades suficientes", { items: problemas });
      }

      // Descuento atómico (en memoria)
      const lineas = [];
      for (const it of items) {
        const p = productos.find(x => x.variants.some(v => v.id === it.variantId));
        const v = p.variants.find(v => v.id === it.variantId);
        v.availableUnits -= it.quantity;
        lineas.push({
          variantId: v.id, productName: p.name, size: v.size,
          quantity: it.quantity, unitPriceCop: p.priceCop,
          subtotalCop: p.priceCop * it.quantity,
        });
      }
      const orden = {
        id: randomUUID(), orderNumber: numeroOrden(), status: "CONFIRMADA",
        items: lineas, totalCop: lineas.reduce((s, l) => s + l.subtotalCop, 0),
        customer: { ...customer, phone: String(customer.phone).replace(/^\+/, "") },
        createdAt: new Date().toISOString(),
      };
      ordenes.unshift(orden);
      return enviar(res, 201, orden);
    }

    // EP-06 · GET /orders/{orderNumber}?email=
    if (m("GET", /^\/orders\/[^/]+$/)) {
      const numero = decodeURIComponent(ruta.split("/")[2]);
      const email = url.searchParams.get("email");
      const o = ordenes.find(x => x.orderNumber === numero && x.customer.email === email);
      if (!o) return fallo(res, 404, "NOT_FOUND", "La orden no existe o los datos no coinciden");
      return enviar(res, 200, o);
    }

    // EP-10 · POST /auth/login
    if (m("POST", /^\/auth\/login$/)) {
      const { email, password } = await leerCuerpo(req);
      if (email === "admin@tiendalocal.co" && password === "tiendalocal2026") {
        return enviar(res, 200, { accessToken: `tok_${randomUUID()}`, tokenType: "Bearer", expiresIn: 3600 });
      }
      return fallo(res, 401, "INVALID_CREDENTIALS", "Correo o contraseña incorrectos");
    }

    // ----- administración: exige token (RNF-04)
    if (ruta.startsWith("/admin")) {
      if (!autenticado(req)) {
        return fallo(res, 401, "UNAUTHENTICATED", "Falta el token o está vencido");
      }

      // EP-24 · GET /admin/inventory
      if (m("GET", /^\/admin\/inventory$/)) {
        const filas = productos.flatMap(p => p.variants.map(v => ({
          variantId: v.id, productId: p.id, productName: p.name, sku: v.sku, size: v.size,
          availableUnits: v.availableUnits, priceCop: p.priceCop,
          categoryName: p.category.name, imageUrl: p.images[0]?.url ?? null,
          published: p.published,
        })));
        return enviar(res, 200, pagina(filas, url));
      }

      // EP-17 · GET /admin/orders
      if (m("GET", /^\/admin\/orders$/)) {
        const filas = ordenes.map(o => ({
          id: o.id, orderNumber: o.orderNumber, status: o.status,
          totalCop: o.totalCop, createdAt: o.createdAt,
          customerName: o.customer.name, itemCount: o.items.length,
        }));
        return enviar(res, 200, pagina(filas, url));
      }

      // EP-15 · PATCH /admin/variants/{id}/inventory
      if (m("PATCH", /^\/admin\/variants\/[^/]+\/inventory$/)) {
        const id = ruta.split("/")[3];
        const { availableUnits } = await leerCuerpo(req);
        if (!Number.isInteger(availableUnits) || availableUnits < 0) {
          return fallo(res, 400, "VALIDATION_ERROR", "Existencias inválidas",
            { fields: [{ field: "availableUnits", issue: "entero mayor o igual que cero" }] });
        }
        const p = productos.find(x => x.variants.some(v => v.id === id));
        const v = p?.variants.find(v => v.id === id);
        if (!v) return fallo(res, 404, "NOT_FOUND", "La variante no existe");
        v.availableUnits = availableUnits;
        return enviar(res, 200, {
          variantId: v.id, productId: p.id, productName: p.name, sku: v.sku,
          size: v.size, availableUnits: v.availableUnits, priceCop: p.priceCop,
          categoryName: p.category.name, imageUrl: p.images[0]?.url ?? null, published: p.published,
        });
      }
    }

    return fallo(res, 404, "NOT_FOUND", "Ruta no encontrada");
  } catch (e) {
    return fallo(res, 500, "INTERNAL_ERROR", e?.message || "Error no controlado");
  }
});

servidor.listen(PUERTO, () => {
  console.log(`Servidor de apoyo escuchando en http://localhost:${PUERTO}/api/v1`);
  console.log(`  ${productos.filter(p => p.published).length} productos publicados, 1 borrador`);
  console.log(`  admin: admin@tiendalocal.co / tiendalocal2026`);
});
