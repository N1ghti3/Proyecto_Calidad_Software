import { useCallback, useEffect, useId, useMemo, useState, type FormEvent, type ReactNode } from "react";
import Admin from "./Admin";
import {
  ApiError, AVISO_PRIVACIDAD, cerrarSesion, consultarOrden, cop, crearOrden, fechaLocal,
  fechaHoraLocal, haySesion, iniciarSesion, listarCatalogoCompleto, listarCategorias,
  obtenerProducto, validarCarrito,
  type CartValidationResponse, type CategoryResponse, type CustomerRequest, type EstadoOrden,
  type OrderResponse, type ProductResponse, type ProductSummaryResponse,
  type ProductVariantResponse,
} from "./api";
import { Foto, Icon } from "./componentes";
import { ContextoNavegacion, Enlace, direccionActual, useNavegacion, type Ir } from "./navegacion";
import { leerRuta, rutas, tituloDe } from "./rutas";

/** Línea del carrito. Compra por variante, nunca por producto (RN-05). */
type ItemCarrito = {
  variantId: string;
  productSlug: string;
  productName: string;
  categoryName: string;
  size: string;
  unitPriceCop: number;
  imageUrl: string | null;
  imageAlt: string | null;
  quantity: number;
  availableUnits: number;
};

/* Imágenes decorativas del diseño (hero y portadas de categoría).
   Las fotografías de producto provienen de la API. */
const photos = {
  hero: "https://images.unsplash.com/photo-1767036840968-91dc63654cd7?auto=format&fit=crop&w=1200&q=85",
  street: "https://images.unsplash.com/photo-1629753453388-5f3ae10370ef?auto=format&fit=crop&w=900&q=85",
  tee: "https://images.unsplash.com/photo-1618718123715-a2db2f17e908?auto=format&fit=crop&w=900&q=85",
  woven: "https://images.unsplash.com/photo-1741188491649-7df9303dd892?auto=format&fit=crop&w=900&q=85",
  jewels: "https://images.unsplash.com/photo-1567736464933-bc179b82a448?auto=format&fit=crop&w=900&q=85",
  shoe: "https://images.unsplash.com/photo-1634801634476-2d98226094fe?auto=format&fit=crop&w=900&q=85",
  basket: "https://images.unsplash.com/photo-1534413340928-7bd74b65196f?auto=format&fit=crop&w=900&q=85",
};

const portadas: Record<string, { image: string; subtitle: string }> = {
  "Chaquetas":    { image: photos.street, subtitle: "Capas urbanas para el clima bogotano" },
  "Ropa exterior": { image: photos.street, subtitle: "Capas urbanas para el clima bogotano" },
  "Camisetas":    { image: photos.tee,    subtitle: "Básicos gráficos de edición local" },
  "Bolsos":       { image: photos.woven,  subtitle: "Tejidos, cuero y fibras naturales" },
  "Artesanías":   { image: photos.woven,  subtitle: "Oficios tradicionales de todo el país" },
  "Joyería":      { image: photos.jewels, subtitle: "Piezas pequeñas hechas a mano" },
  "Accesorios":   { image: photos.jewels, subtitle: "Piezas pequeñas hechas a mano" },
  "Calzado":      { image: photos.shoe,   subtitle: "Diseño cómodo para recorrer la ciudad" },
  "Hogar & arte": { image: photos.basket, subtitle: "Objetos con oficio y memoria" },
};

/** Lo mínimo de un pedido para listarlo en «Mis pedidos». Sin datos del
 *  comprador: esto se guarda en el navegador. */
type PedidoSesion = Pick<OrderResponse, "orderNumber" | "status" | "totalCop" | "createdAt">;

/* Memoria del navegador.
 *
 * Con una ruta por sección, recargar /carrito o /pago es un gesto normal, y
 * vaciar el carrito al hacerlo sería un error. El carrito y los favoritos se
 * guardan en localStorage: no contienen datos personales. Los pedidos de la
 * sesión van a sessionStorage y solo con número, estado y total.
 *
 * Toda lectura y escritura tolera fallos: en una ventana privada o con el
 * almacenamiento bloqueado la tienda sigue funcionando, solo que olvida.
 */
function leerGuardado<T>(almacen: "local" | "session", clave: string, porDefecto: T): T {
  try {
    const crudo = (almacen === "local" ? window.localStorage : window.sessionStorage).getItem(clave);
    return crudo ? (JSON.parse(crudo) as T) : porDefecto;
  } catch { return porDefecto; }
}

function useGuardado<T>(almacen: "local" | "session", clave: string, porDefecto: T) {
  const [valor, setValor] = useState<T>(() => leerGuardado(almacen, clave, porDefecto));
  useEffect(() => {
    try {
      (almacen === "local" ? window.localStorage : window.sessionStorage).setItem(clave, JSON.stringify(valor));
    } catch { /* almacenamiento no disponible: se sigue sin recordar */ }
  }, [almacen, clave, valor]);
  return [valor, setValor] as const;
}

const ETIQUETA_ESTADO: Record<EstadoOrden, string> = {
  CONFIRMADA: "Confirmado", PREPARADA: "En preparación", ENTREGADA: "Entregado", CANCELADA: "Cancelado",
};

const tonos = ["clay", "sand", "sky", "sage", "peach", "rose", "lilac", "mint"];
/** Tono visual estable derivado del identificador, para que no cambie entre cargas. */
const tono = (id: string) => tonos[[...id].reduce((s, c) => s + c.charCodeAt(0), 0) % tonos.length];

/** Etiqueta derivada del inventario real, no un texto decorativo. */
function insignia(p: ProductSummaryResponse): { texto: string; verde: boolean } | null {
  if (!p.inStock) return { texto: "Agotado", verde: false };
  if (p.availableUnits <= 5) return { texto: "Últimas unidades", verde: false };
  if (p.availableUnits >= 40) return { texto: "Top ventas", verde: true };
  return null;
}

/** Acciones de la tienda que las tarjetas de producto necesitan en cualquier página. */
type Acciones = {
  saved: string[];
  toggle: (id: string) => void;
  add: (p: ProductSummaryResponse) => void;
};

function Header({ search, favCount, cartCount }: { search: () => void; favCount: number; cartCount: number }) {
  const [open, setOpen] = useState(false);
  const cerrar = () => setOpen(false);
  return (
    <header className="header">
      <Enlace a={rutas.inicio} className="logo" onClick={cerrar}>Tienda<span>Local</span></Enlace>
      <nav className={open ? "nav open" : "nav"} aria-label="Principal">
        <Enlace a={rutas.inicio} activo="exacto" onClick={cerrar}>Inicio</Enlace>
        <Enlace a={rutas.catalogo} activo="exacto" onClick={cerrar}>Catálogo</Enlace>
        <Enlace a={rutas.categorias} activo="prefijo" onClick={cerrar}>Categorías</Enlace>
        <Enlace a={rutas.artesanos} activo="exacto" onClick={cerrar}>Artesanos</Enlace>
      </nav>
      <div className="header-actions">
        <button className="icon-btn search-btn" aria-label="Buscar" onClick={search}><Icon name="search"/></button>
        <Enlace a={rutas.favoritos} className="icon-btn" aria-label={`Favoritos (${favCount})`}><Icon name="heart"/>{favCount > 0 && <b aria-hidden="true">{favCount}</b>}</Enlace>
        <Enlace a={rutas.carrito} className="icon-btn" aria-label={`Carrito (${cartCount})`}><Icon name="bag"/>{cartCount > 0 && <b aria-hidden="true">{cartCount}</b>}</Enlace>
        <Enlace a={rutas.perfil} className="icon-btn" aria-label="Mis pedidos"><Icon name="user"/></Enlace>
        <button className="icon-btn menu-btn" aria-label="Menú" aria-expanded={open} onClick={() => setOpen(!open)}><Icon name={open ? "close" : "menu"}/></button>
      </div>
    </header>
  );
}

function ProductCard({ product, saved, toggle, add }: {
  product: ProductSummaryResponse; saved: boolean; toggle: () => void; add: () => void;
}) {
  const { ir } = useNavegacion();
  const marca = insignia(product);
  const destino = rutas.producto(product.slug);
  return (
    <article className="product-card">
      <div className={`product-image ${tono(product.id)}`}>
        {/* La imagen también abre el detalle, pero el enlace accesible es el
            título de abajo: dos enlaces al mismo destino se anuncian dos veces. */}
        <Foto src={product.imageUrl} alt={product.imageAlt ?? product.name}
              onClick={() => ir(destino)} loading="lazy"/>
        {marca && <span className={marca.verde ? "badge green" : "badge"}>{marca.texto}</span>}
        <button className={`heart ${saved ? "saved" : ""}`} onClick={toggle} aria-pressed={saved}
                aria-label={saved ? `Quitar ${product.name} de favoritos` : `Guardar ${product.name} en favoritos`}>
          <Icon name="heart" filled={saved}/>
        </button>
        <button className="quick-add" onClick={add} disabled={!product.inStock}>
          {product.inStock ? <>Agregar al carrito <Icon name="plus"/></> : "Sin existencias"}
        </button>
      </div>
      <Enlace a={destino} className="product-copy">
        <span>{product.categoryName}</span>
        <strong>{product.name}</strong>
        <div><em>{cop(product.priceCop)}</em><small>{product.availableUnits} disponibles</small></div>
      </Enlace>
    </article>
  );
}

function Grilla({ productos, acciones }: { productos: ProductSummaryResponse[]; acciones: Acciones }) {
  return (
    <div className="product-grid">
      {productos.map(p => <ProductCard key={p.id} product={p} saved={acciones.saved.includes(p.id)}
        toggle={() => acciones.toggle(p.id)} add={() => acciones.add(p)}/>)}
    </div>
  );
}

/** Estante de una categoría: título numerado y sus productos. */
function Estante({ categoria, indice, productos, acciones, enlazar = true }: {
  categoria: CategoryResponse; indice: number; productos: ProductSummaryResponse[];
  acciones: Acciones; enlazar?: boolean;
}) {
  return (
    <section className="category-shelf section">
      <div className="category-title">
        <span>{String(indice + 1).padStart(2, "0")}</span>
        <div>
          <h2>{enlazar ? <Enlace a={rutas.categoria(categoria.slug)}>{categoria.name}</Enlace> : categoria.name}</h2>
          <p>{portadas[categoria.name]?.subtitle ?? "Piezas de talleres locales"}</p>
        </div>
        <small>{productos.length} productos</small>
      </div>
      <Grilla productos={productos} acciones={acciones}/>
    </section>
  );
}

function FilaCategorias({ categorias }: { categorias: CategoryResponse[] }) {
  return (
    <div className="category-row">
      {categorias.map((c, i) => (
        <Enlace key={c.id} a={rutas.categoria(c.slug)}>
          <span><img src={portadas[c.name]?.image ?? photos.hero} alt=""
                     loading="lazy" decoding="async"/><b aria-hidden="true">{String(i + 1).padStart(2, "0")}</b></span>
          <strong>{c.name}</strong><small>{c.productCount} productos</small>
        </Enlace>
      ))}
    </div>
  );
}

function Promos({ productos }: { productos: ProductSummaryResponse[] }) {
  return (
    <section className="promos section" aria-label="Destacados">
      <article className="promo orange">
        <span>Solo esta semana</span><h2>Hasta 30% en accesorios</h2>
        <Enlace a={rutas.catalogo} className="promo-enlace">Comprar ahora <Icon name="arrow"/></Enlace>
      </article>
      <article className="promo dark">
        <span>Edición limitada</span><h2>Piezas artesanales de temporada</h2>
        <Enlace a={productos[0] ? rutas.producto(productos[0].slug) : rutas.artesanos} className="promo-enlace">
          Descubrir <Icon name="arrow"/></Enlace>
      </article>
    </section>
  );
}

/* ------------------------------------------------------------------ páginas */

function Home({ productos, categorias, acciones }: {
  productos: ProductSummaryResponse[]; categorias: CategoryResponse[]; acciones: Acciones;
}) {
  const nuevos = productos.slice(0, 4);
  const masVendidos = useMemo(
    () => [...productos].sort((a, b) => b.availableUnits - a.availableUnits).slice(0, 4),
    [productos],
  );

  const seccion = (title: string, items: ProductSummaryResponse[]) => (
    <section className="section">
      <div className="section-head">
        <div><span className="eyebrow">Selección local</span><h2>{title}</h2></div>
        <Enlace a={rutas.catalogo}>Ver todo <Icon name="arrow"/></Enlace>
      </div>
      <Grilla productos={items} acciones={acciones}/>
    </section>
  );

  return (
    <main>
      <section className="hero">
        <div className="hero-copy">
          <span className="kicker">Colección nueva · Hecho en Bogotá</span>
          <h1>Descubre piezas que <i>no vas a encontrar</i> en otro lado.</h1>
          <p>Moda urbana y artesanías directo del taller a tu puerta, con disponibilidad real.</p>
          <div className="hero-actions">
            <Enlace a={rutas.catalogo} className="primary">Ver catálogo <Icon name="arrow"/></Enlace>
            <Enlace a={rutas.artesanos} className="secondary">Conocer artesanos</Enlace>
          </div>
        </div>
        <div className="hero-visual">
          {/* La única imagen que sí conviene pedir de inmediato: es lo
              primero que se ve y marca el momento en que la página deja de
              parecer vacía. El resto carga de forma diferida. */}
          <div className="shape"></div>
          <img src={photos.hero} alt="Moda urbana de nueva colección"
               fetchPriority="high" decoding="async"/>
          {productos[12] && <div className="floating one"><Foto src={productos[12].imageUrl} alt={productos[12].imageAlt ?? productos[12].name}/><span>{productos[12].name}<strong>{cop(productos[12].priceCop)}</strong></span></div>}
          {productos[9] && <div className="floating two"><Foto src={productos[9].imageUrl} alt={productos[9].imageAlt ?? productos[9].name}/><span>{productos[9].name}<strong>{cop(productos[9].priceCop)}</strong></span></div>}
          <span className="local-stamp">100%<br/>LOCAL</span>
        </div>
      </section>

      <div className="benefits">
        <div><Icon name="truck"/><span><strong>Envío en Bogotá</strong>Rápido y seguro</span></div>
        <div><Icon name="bag"/><span><strong>Pago contra entrega</strong>Compra con confianza</span></div>
        <div><Icon name="refresh"/><span><strong>Cambios fáciles</strong>Hasta 15 días</span></div>
        <div><Icon name="message"/><span><strong>Soporte directo</strong>Habla con nosotros</span></div>
      </div>

      <section className="categories section">
        <div className="section-head">
          <div><span className="eyebrow">Encuentra tu estilo</span><h2>Comprar por categoría</h2></div>
          <Enlace a={rutas.categorias}>Todas las categorías <Icon name="arrow"/></Enlace>
        </div>
        <FilaCategorias categorias={categorias}/>
      </section>

      {seccion("Nuevos ingresos", nuevos)}
      {seccion("Los más vendidos", masVendidos)}
      <Promos productos={productos}/>
    </main>
  );
}

function Catalogo({ productos, categorias, acciones }: {
  productos: ProductSummaryResponse[]; categorias: CategoryResponse[]; acciones: Acciones;
}) {
  return (
    <main>
      <section className="catalog-intro section">
        <span className="eyebrow">Catálogo completo</span>
        <div>
          <h1>Más diseño local,<br/>más formas de encontrar tu estilo.</h1>
          <p>Explora {productos.length} piezas creadas por talleres independientes de Bogotá. Cada colección reúne materiales, oficios y miradas diferentes.</p>
        </div>
        <nav aria-label="Categorías del catálogo">
          {categorias.map(c => (
            <Enlace key={c.id} a={rutas.categoria(c.slug)}>{c.name}<span>{c.productCount}</span></Enlace>
          ))}
        </nav>
      </section>
      <div className="category-catalog">
        {categorias.map((c, i) => {
          const items = productos.filter(p => p.categoryName === c.name);
          return items.length ? <Estante key={c.id} categoria={c} indice={i} productos={items} acciones={acciones}/> : null;
        })}
      </div>
    </main>
  );
}

function Categorias({ categorias }: { categorias: CategoryResponse[] }) {
  return (
    <main className="page collection-page">
      <span className="eyebrow">Encuentra tu estilo</span>
      <h1>Categorías</h1>
      <p>{categorias.length} colecciones de talleres independientes.</p>
      <div className="categorias-grid">
        {categorias.map(c => (
          <Enlace key={c.id} a={rutas.categoria(c.slug)} className="categoria-tarjeta">
            <img src={portadas[c.name]?.image ?? photos.hero} alt="" loading="lazy" decoding="async"/>
            <span><strong>{c.name}</strong><small>{portadas[c.name]?.subtitle ?? "Piezas de talleres locales"}</small>
              <em>{c.productCount} productos <Icon name="arrow"/></em></span>
          </Enlace>
        ))}
      </div>
    </main>
  );
}

function Categoria({ categoria, indice, productos, acciones }: {
  categoria: CategoryResponse; indice: number; productos: ProductSummaryResponse[]; acciones: Acciones;
}) {
  const items = productos.filter(p => p.categoryName === categoria.name);
  return (
    <main className="page collection-page">
      <nav className="breadcrumb" aria-label="Ruta de navegación">
        <Enlace a={rutas.inicio}>Inicio</Enlace> / <Enlace a={rutas.categorias}>Categorías</Enlace> / <b>{categoria.name}</b>
      </nav>
      <h1>{categoria.name}</h1>
      <p>{portadas[categoria.name]?.subtitle ?? "Piezas de talleres locales"} · {items.length} productos</p>
      {items.length
        ? <Grilla productos={items} acciones={acciones}/>
        : <div className="empty"><Icon name="bag"/><h2>Esta categoría aún no tiene productos publicados</h2>
            <Enlace a={rutas.catalogo} className="primary">Ver todo el catálogo</Enlace></div>}
    </main>
  );
}

function Artesanos({ productos, categorias, acciones }: {
  productos: ProductSummaryResponse[]; categorias: CategoryResponse[]; acciones: Acciones;
}) {
  const artesanias = categorias.find(c => c.slug === "artesanias");
  const piezas = artesanias ? productos.filter(p => p.categoryName === artesanias.name) : [];
  return (
    <main>
      <section className="page collection-page artesanos-intro">
        <span className="eyebrow">Hecho a mano</span>
        <h1>Nuestros artesanos</h1>
        <p>TiendaLocal reúne talleres independientes de Bogotá y oficios tradicionales de todo el país:
           tejido wayuu de La Guajira, caña flecha del Caribe, cerámica de Ráquira y hamacas de San Jacinto.
           Cada pieza llega directo del taller, con inventario real.</p>
      </section>
      <Promos productos={productos}/>
      {artesanias && piezas.length > 0 &&
        <Estante categoria={artesanias} indice={0} productos={piezas} acciones={acciones}/>}
    </main>
  );
}

function NoEncontrada({ mensaje }: { mensaje?: string }) {
  return (
    <main className="page">
      <div className="empty">
        <Icon name="search"/>
        <h1 className="no-encontrada">Página no encontrada</h1>
        <p>{mensaje ?? "La dirección que abriste no existe o cambió."}</p>
        <Enlace a={rutas.catalogo} className="primary">Ir al catálogo <Icon name="arrow"/></Enlace>
      </div>
    </main>
  );
}

function Field({ label, placeholder, type = "text", name, required = false, pattern, title, defaultValue, autoComplete }: {
  label: string; placeholder: string; type?: string; name?: string;
  required?: boolean; pattern?: string; title?: string; defaultValue?: string; autoComplete?: string;
}) {
  // Asociación explícita etiqueta–campo: algunas tecnologías de apoyo toman
  // el placeholder como nombre cuando el campo solo está anidado en la etiqueta.
  const id = useId();
  return (
    <label className="field" htmlFor={id}><span>{label}</span>
      <input id={id} type={type} name={name} placeholder={placeholder} required={required}
             pattern={pattern} title={title} defaultValue={defaultValue} autoComplete={autoComplete}/>
    </label>
  );
}

/** Ingreso al panel. Los compradores no tienen cuenta (el checkout no la
 *  exige): la pestaña Cliente ya no simula un inicio de sesión que no
 *  existía, sino que lleva a la consulta de pedidos por número y correo. */
function Login({ volver, entrarAdmin }: {
  volver: string | null; entrarAdmin: (email: string, clave: string) => Promise<void>;
}) {
  const [role, setRole] = useState<"client" | "admin">(volver ? "admin" : "client");
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const enviar = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null); setEnviando(true);
    const datos = new FormData(e.currentTarget);
    try {
      await entrarAdmin(String(datos.get("email") || ""), String(datos.get("password") || ""));
    } catch (err) {
      setError(err instanceof ApiError && err.code === "INVALID_CREDENTIALS"
        ? "Correo o contraseña incorrectos."
        : err instanceof ApiError && err.code === "RATE_LIMITED"
          ? `Demasiados intentos. Espera ${(err.details.retryAfterSeconds as number) ?? 60} segundos.`
          : err instanceof Error ? err.message : "No se pudo iniciar sesión.");
    } finally { setEnviando(false); }
  };

  return (
    <div className={`login-page ${role === "admin" ? "admin-mode" : ""}`}>
      <Enlace a={rutas.inicio} className="back-home"><Icon name="arrow"/> Volver a la tienda</Enlace>
      <div className="login-art">
        <Enlace a={rutas.inicio} className="logo">Tienda<span>Local</span></Enlace>
        <div><span className="kicker">Compra local. Viste diferente.</span><h2>Diseño con origen,<br/>historias con futuro.</h2><p>Conectamos el talento independiente de Bogotá con personas que valoran lo auténtico.</p></div>
        <small>Hecho por manos locales — Bogotá, Colombia</small>
      </div>
      <main className="login-card">
        <div className="login-title"><span>TL</span><h1>Bienvenido a TiendaLocal</h1>
          <p>{role === "admin" ? "Ingresa al panel de tu negocio." : "Para comprar no necesitas cuenta."}</p></div>
        <div className="role-switch" role="group" aria-label="Tipo de acceso">
          <button className={role === "client" ? "active" : ""} aria-pressed={role === "client"} onClick={() => { setRole("client"); setError(null); }}>Cliente</button>
          <button className={role === "admin" ? "active" : ""} aria-pressed={role === "admin"} onClick={() => { setRole("admin"); setError(null); }}>Administrador</button>
        </div>
        {role === "client" ? (
          <div className="cliente-info">
            <p>Compras sin registrarte. Al confirmar recibes un número de pedido; con ese número y tu correo puedes ver su estado cuando quieras.</p>
            <Enlace a={rutas.consultar()} className="submit">Consultar un pedido <Icon name="arrow"/></Enlace>
            <Enlace a={rutas.catalogo} className="secondary cliente-catalogo">Ir al catálogo</Enlace>
          </div>
        ) : (
          <form onSubmit={enviar}>
            {volver && <p className="admin-note"><Icon name="grid"/><span>Tu sesión se cerró al recargar la página. Ingresa de nuevo para volver a donde estabas.</span></p>}
            <Field label="Correo electrónico del negocio" placeholder="hola@tunegocio.co" type="email" name="email" required autoComplete="username"/>
            <label className="field"><span>Contraseña</span>
              <div><input type={show ? "text" : "password"} name="password" autoComplete="current-password"
                          placeholder="Mínimo 8 caracteres" required/>
                <button type="button" onClick={() => setShow(!show)} aria-pressed={show} aria-label="Mostrar contraseña"><Icon name="eye"/></button></div>
            </label>
            {error && <div className="stock-warning" role="alert">{error}</div>}
            <button className="submit" type="submit" disabled={enviando}>
              {enviando ? "Entrando…" : "Entrar al panel"} <Icon name="arrow"/>
            </button>
            <div className="admin-note"><Icon name="grid"/><span><strong>Acceso exclusivo para negocios</strong>Gestiona catálogo, inventario y pedidos. Si vas a comprar, usa la pestaña Cliente.</span></div>
          </form>
        )}
      </main>
    </div>
  );
}

function ProductDetail({ producto, relacionados, saved, toggle, agregar, acciones }: {
  producto: ProductResponse; relacionados: ProductSummaryResponse[]; saved: boolean; toggle: () => void;
  agregar: (p: ProductResponse, v: ProductVariantResponse, cantidad: number) => void; acciones: Acciones;
}) {
  const [variantId, setVariantId] = useState<string | null>(null);
  const [qty, setQty] = useState(1);
  const [foto, setFoto] = useState(0);

  useEffect(() => {
    const primera = producto.variants.find(v => v.inStock);
    setVariantId(primera?.id ?? null);
    setQty(1); setFoto(0);
  }, [producto.id]);

  const variante = producto.variants.find(v => v.id === variantId) ?? null;
  const maximo = variante?.availableUnits ?? 0;
  const imagen = producto.images[foto] ?? producto.images[0];
  const imagenPrincipal = imagen?.url ?? producto.imageUrl;
  const altPrincipal = imagen?.alt ?? producto.imageAlt ?? producto.name;

  return (
    <main className="detail page">
      <nav className="breadcrumb" aria-label="Ruta de navegación">
        <Enlace a={rutas.inicio}>Inicio</Enlace> / <Enlace a={rutas.categoria(producto.category.slug)}>{producto.category.name}</Enlace> / <b>{producto.name}</b>
      </nav>
      <div className="detail-grid">
        <div className="gallery">
          <div className="main-photo"><Foto src={imagenPrincipal} alt={altPrincipal} loading="eager"/></div>
          {producto.images.length > 1 && (
            <div className="thumbs" role="group" aria-label="Fotografías del producto">
              {producto.images.map((img, i) => (
                <button key={img.id} className={i === foto ? "active" : ""} aria-pressed={i === foto}
                        aria-label={`Ver fotografía ${i + 1} de ${producto.images.length}`} onClick={() => setFoto(i)}>
                  <Foto src={img.url} alt=""/>
                </button>
              ))}
            </div>
          )}
        </div>
        <section className="product-info">
          <span className="eyebrow">{producto.category.name} · {variante?.sku ?? producto.variants[0]?.sku ?? producto.slug}</span>
          <h1>{producto.name}</h1>
          <p className="detail-price">{cop(producto.priceCop)} <small>IVA incluido</small></p>
          <p className="stock">
            {producto.inStock
              ? `● Disponible — ${producto.availableUnits} unidades`
              : "● Sin existencias por el momento"}
          </p>
          {producto.description && <p className="intro">{producto.description}</p>}

          <div className="options">
            <div><strong id="titulo-tallas">{producto.variants.length > 1 ? "Selecciona tu talla" : "Presentación"}</strong></div>
            <div className="chips" role="group" aria-labelledby="titulo-tallas">
              {producto.variants.map(v => (
                <button key={v.id}
                        className={variantId === v.id ? "active" : ""}
                        aria-pressed={variantId === v.id}
                        disabled={!v.inStock}
                        title={v.inStock ? `${v.availableUnits} disponibles` : "Agotada"}
                        onClick={() => { setVariantId(v.id); setQty(1); }}>
                  {v.size}
                </button>
              ))}
            </div>
            {variante && <p className="stock" style={{ marginTop: ".4rem" }}>
              Talla {variante.size}: {variante.availableUnits} {variante.availableUnits === 1 ? "unidad" : "unidades"}
            </p>}
          </div>

          <div className="purchase">
            <div className="stepper">
              <button onClick={() => setQty(Math.max(1, qty - 1))} aria-label="Quitar una unidad"><Icon name="minus"/></button>
              <span aria-live="polite" aria-label={`Cantidad: ${qty}`}>{qty}</span>
              <button onClick={() => setQty(Math.min(maximo, qty + 1))} aria-label="Agregar una unidad" disabled={qty >= maximo}><Icon name="plus"/></button>
            </div>
            <button className="primary" disabled={!variante || maximo === 0}
                    onClick={() => variante && agregar(producto, variante, qty)}>
              {maximo === 0 ? "Sin existencias" : <>Agregar al carrito <Icon name="bag"/></>}
            </button>
            <button className={`detail-heart ${saved ? "saved" : ""}`} onClick={toggle} aria-pressed={saved}
                    aria-label={saved ? "Quitar de favoritos" : "Guardar en favoritos"}>
              <Icon name="heart" filled={saved}/>
            </button>
          </div>

          <div className="accordions">
            <details open><summary>Detalles<Icon name="plus"/></summary><p>{producto.description ?? "Pieza elaborada por talleres independientes de Bogotá."}</p></details>
            <details><summary>Material y cuidado<Icon name="plus"/></summary><p>Consulta toda la información y recomendaciones para cuidar esta pieza.</p></details>
            <details><summary>Envío y cambios<Icon name="plus"/></summary><p>Envío en Bogotá. Cambios hasta 15 días después de la entrega.</p></details>
          </div>
        </section>
      </div>
      {relacionados.length > 0 && (
        <section className="section related">
          <div className="section-head"><div><span className="eyebrow">Sigue explorando</span><h2>También te puede interesar</h2></div></div>
          <Grilla productos={relacionados} acciones={acciones}/>
        </section>
      )}
    </main>
  );
}

function Favorites({ productos, acciones }: { productos: ProductSummaryResponse[]; acciones: Acciones }) {
  const all = productos.filter(p => acciones.saved.includes(p.id));
  return (
    <main className="page collection-page">
      <span className="eyebrow">Tu selección</span>
      <h1>Mis favoritos</h1>
      <p>{all.length} productos guardados</p>
      {all.length ? <Grilla productos={all} acciones={acciones}/> : (
        <div className="empty"><Icon name="heart"/><h2>Aún no has guardado productos</h2>
          <p>Marca con el corazón las piezas que no quieres perder de vista.</p>
          <Enlace a={rutas.catalogo} className="primary">Explorar catálogo</Enlace></div>
      )}
    </main>
  );
}

function Cart({ items, validacion, cambiar, quitar }: {
  items: ItemCarrito[]; validacion: CartValidationResponse | null;
  cambiar: (variantId: string, cantidad: number) => void; quitar: (variantId: string) => void;
}) {
  const subtotal = items.reduce((s, i) => s + i.unitPriceCop * i.quantity, 0);
  const faltantes = validacion?.items.filter(l => !l.available) ?? [];
  // El total sale del servidor (modelos.md): mientras la validación llega,
  // se muestra el cálculo local para no dejar el resumen vacío.
  const total = validacion?.valid ? validacion.totalCop : subtotal;
  return (
    <main className="page cart-page">
      <span className="eyebrow">Tu compra</span>
      <h1>Carrito <small>({items.reduce((s, i) => s + i.quantity, 0)} productos)</small></h1>
      <div className="cart-layout">
        <section className="cart-list" aria-label="Productos en el carrito">
          {faltantes.length > 0 && (
            <div className="stock-warning" role="alert">
              <strong>Algunas unidades ya no están disponibles.</strong>
              <ul>{faltantes.map(l => <li key={l.variantId}>{l.productName} talla {l.size}: pediste {l.requestedQuantity}, quedan {l.availableUnits}</li>)}</ul>
              Ajusta las cantidades para continuar.
            </div>
          )}
          {items.length ? items.map(item => (
            <article className="cart-item" key={item.variantId}>
              <Foto src={item.imageUrl} alt={item.imageAlt ?? item.productName}/>
              <div>
                <span>{item.categoryName}</span>
                <h3><Enlace a={rutas.producto(item.productSlug)}>{item.productName}</Enlace></h3>
                <p>Talla: {item.size}</p>
                <div className="stepper">
                  <button onClick={() => cambiar(item.variantId, item.quantity - 1)} aria-label={`Quitar una unidad de ${item.productName}`}><Icon name="minus"/></button>
                  <span>{item.quantity}</span>
                  <button onClick={() => cambiar(item.variantId, item.quantity + 1)} aria-label={`Agregar una unidad de ${item.productName}`} disabled={item.quantity >= item.availableUnits}><Icon name="plus"/></button>
                </div>
                {item.quantity >= item.availableUnits && <p className="stock-warning">Solo quedan {item.availableUnits} unidades disponibles</p>}
              </div>
              <strong>{cop(item.unitPriceCop * item.quantity)}</strong>
              <button className="remove" onClick={() => quitar(item.variantId)} aria-label={`Eliminar ${item.productName}`}><Icon name="trash"/></button>
            </article>
          )) : (
            <div className="empty"><Icon name="bag"/><h2>Tu carrito está vacío</h2>
              <Enlace a={rutas.catalogo} className="primary">Explorar catálogo</Enlace></div>
          )}
        </section>
        <aside className="summary">
          <h2>Resumen de compra</h2>
          <div><span>Subtotal</span><strong>{cop(subtotal)}</strong></div>
          <div><span>Envío</span><strong>Calculado al pagar</strong></div>
          <hr/>
          <div className="total"><span>Total</span><strong>{cop(total)}</strong></div>
          {items.length > 0 && faltantes.length === 0
            ? <Enlace a={rutas.pago} className="primary">Continuar al pago <Icon name="arrow"/></Enlace>
            : <button className="primary" disabled>Continuar al pago <Icon name="arrow"/></button>}
          <small>{validacion ? "Disponibilidad comprobada hace un momento; no se reservan unidades hasta confirmar." : "Pago seguro · Checkout simulado con fines académicos"}</small>
        </aside>
      </div>
    </main>
  );
}

function Checkout({ items, orden, confirmar }: {
  items: ItemCarrito[];
  orden: OrderResponse | null;
  confirmar: (cliente: CustomerRequest, consentimiento: boolean) => Promise<OrderResponse>;
}) {
  const [error, setError] = useState<string | null>(null);
  const [faltantes, setFaltantes] = useState<string[]>([]);
  const [enviando, setEnviando] = useState(false);
  const total = items.reduce((s, i) => s + i.unitPriceCop * i.quantity, 0);

  if (orden) {
    return (
      <main className="page checkout-page">
        <div className="checkout-success">
          <span><Icon name="check"/></span>
          <p className="eyebrow">Pedido confirmado</p>
          <h1>¡Gracias por comprar local!</h1>
          <p>Tu pedido <strong>#{orden.orderNumber}</strong> fue registrado por {cop(orden.totalCop)}.
             Guarda ese número: con él y tu correo puedes consultar el estado.</p>
          <p className="stock-warning">Pago simulado: esta operación no generó ningún cobro real.</p>
          <div className="hero-actions">
            <Enlace a={rutas.consultar(orden.orderNumber)} className="primary">Consultar el estado <Icon name="arrow"/></Enlace>
            <Enlace a={rutas.catalogo} className="secondary">Seguir comprando</Enlace>
          </div>
        </div>
      </main>
    );
  }

  if (!items.length) {
    return (
      <main className="page checkout-page">
        <div className="empty"><Icon name="bag"/><h1 className="no-encontrada">No hay nada que pagar</h1>
          <p>Tu carrito está vacío.</p>
          <Enlace a={rutas.catalogo} className="primary">Explorar catálogo</Enlace></div>
      </main>
    );
  }

  const enviar = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null); setFaltantes([]); setEnviando(true);
    const datos = new FormData(e.currentTarget);
    try {
      await confirmar({
        name: String(datos.get("name") || ""),
        email: String(datos.get("email") || ""),
        phone: String(datos.get("phone") || ""),
        address: String(datos.get("address") || ""),
        city: String(datos.get("city") || ""),
      }, datos.get("consent") === "on");
    } catch (err) {
      if (err instanceof ApiError && err.code === "INSUFFICIENT_STOCK") {
        setFaltantes(err.lineasSinStock.map(l =>
          `${l.productName} talla ${l.size}: pediste ${l.requestedQuantity}, quedan ${l.availableUnits}`));
        setError("Mientras completabas el pedido, alguien compró algunas de estas unidades.");
      } else if (err instanceof ApiError && err.code === "CONSENT_REQUIRED") {
        setError("Debes autorizar el tratamiento de datos para continuar.");
      } else if (err instanceof ApiError && err.code === "VALIDATION_ERROR") {
        const campos = (err.details.fields as { field: string; issue: string }[]) ?? [];
        setError("Revisa los datos del formulario.");
        setFaltantes(campos.map(c => `${c.field}: ${c.issue}`));
      } else {
        setError(err instanceof Error ? err.message : "No pudimos registrar el pedido.");
      }
    } finally { setEnviando(false); }
  };

  return (
    <main className="page checkout-page">
      <Enlace a={rutas.carrito} className="breadcrumb">← Volver al carrito</Enlace>
      <span className="eyebrow">Pago seguro</span>
      <h1>Finaliza tu compra</h1>
      <div className="checkout-layout">
        <form className="checkout-form" onSubmit={enviar}>
          <section>
            <h2>Datos de entrega</h2>
            <div className="form-row">
              <Field label="Nombre completo" placeholder="Ana Ríos" name="name" required autoComplete="name"/>
              <Field label="Correo electrónico" placeholder="ana@correo.com" type="email" name="email" required autoComplete="email"/>
            </div>
            <div className="form-row">
              <Field label="Teléfono" placeholder="+57 300 000 0000" name="phone" required autoComplete="tel"
                     pattern="^\+?[0-9]{7,15}$"
                     title="Entre 7 y 15 dígitos, con + opcional al inicio"/>
              <Field label="Ciudad" placeholder="Bogotá D.C." name="city" required autoComplete="address-level2"/>
            </div>
            <Field label="Dirección" placeholder="Calle 45 # 12-34, apto 201" name="address" required autoComplete="street-address"/>
          </section>
          <fieldset className="checkout-pago">
            <legend><h2>Método de pago</h2></legend>
            <label className="payment-option"><input type="radio" name="payment" defaultChecked/>
              <span><strong>Pago contra entrega</strong><small>Paga en efectivo o transferencia al recibir.</small></span></label>
            <label className="payment-option"><input type="radio" name="payment"/>
              <span><strong>Tarjeta de prueba</strong><small>Checkout simulado; no se realizará ningún cobro.</small></span></label>
          </fieldset>
          {/* RN-16 · Ley 1581 de 2012: sin consentimiento el servidor responde CONSENT_REQUIRED. */}
          <label className="check"><input type="checkbox" name="consent" required/>
            <span>Autorizo el tratamiento de mis datos personales con la única finalidad de
                  gestionar y entregar este pedido (aviso de privacidad v{AVISO_PRIVACIDAD}).</span></label>
          {error && <div className="stock-warning" role="alert">
            <strong>{error}</strong>
            {faltantes.length > 0 && <ul>{faltantes.map(f => <li key={f}>{f}</li>)}</ul>}
          </div>}
          <button className="primary" type="submit" disabled={enviando}>
            {enviando ? "Confirmando…" : <>Confirmar pedido por {cop(total)} <Icon name="check"/></>}
          </button>
        </form>
        <aside className="summary">
          <h2>Tu pedido</h2>
          {items.map(i => (
            <div key={i.variantId}><span>{i.quantity} × {i.productName} ({i.size})</span><strong>{cop(i.unitPriceCop * i.quantity)}</strong></div>
          ))}
          <div><span>Envío en Bogotá</span><strong>Gratis</strong></div>
          <hr/>
          <div className="total"><span>Total</span><strong>{cop(total)}</strong></div>
        </aside>
      </div>
    </main>
  );
}

/** EP-06. La consulta exige número **y** correo (RN-18); el servidor responde
 *  con el correo y el teléfono enmascarados. */
function ConsultarPedido({ numeroInicial }: { numeroInicial: string }) {
  const [orden, setOrden] = useState<OrderResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const enviar = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const datos = new FormData(e.currentTarget);
    setError(null); setOrden(null); setEnviando(true);
    try {
      setOrden(await consultarOrden(String(datos.get("numero")).trim().toUpperCase(), String(datos.get("email")).trim()));
    } catch (err) {
      setError(err instanceof ApiError && err.code === "NOT_FOUND"
        ? "No encontramos un pedido con ese número y ese correo. Revisa que sean los mismos que usaste al comprar."
        : err instanceof Error ? err.message : "No se pudo consultar el pedido.");
    } finally { setEnviando(false); }
  };

  return (
    <main className="page consulta-page">
      <span className="eyebrow">Seguimiento</span>
      <h1>Consultar pedido</h1>
      <p className="consulta-intro">Escribe el número que recibiste al confirmar la compra y el correo con el que la hiciste.</p>
      <div className="checkout-layout">
        <form className="checkout-form" onSubmit={enviar}>
          <section>
            <div className="form-row">
              <Field label="Número de pedido" placeholder="TL-20261020-ABCDE" name="numero" required defaultValue={numeroInicial}/>
              <Field label="Correo electrónico" placeholder="ana@correo.com" type="email" name="email" required autoComplete="email"/>
            </div>
            <button className="primary" type="submit" disabled={enviando}>{enviando ? "Consultando…" : <>Consultar <Icon name="search"/></>}</button>
          </section>
          {error && <div className="stock-warning" role="alert">{error}</div>}
        </form>
        <aside className="summary" aria-live="polite">
          {orden ? <>
            <h2>#{orden.orderNumber}</h2>
            <div><span>Estado</span><strong className={`estado estado-${orden.status.toLowerCase()}`}>{ETIQUETA_ESTADO[orden.status]}</strong></div>
            {orden.createdAt && <div><span>Registrado</span><strong>{fechaHoraLocal(orden.createdAt)}</strong></div>}
            <hr/>
            {orden.items.map(l => (
              <div key={l.variantId}><span>{l.quantity} × {l.productName} ({l.size})</span><strong>{cop(l.lineTotalCop)}</strong></div>
            ))}
            <hr/>
            <div className="total"><span>Total</span><strong>{cop(orden.totalCop)}</strong></div>
            <div><span>Entrega en</span><strong>{orden.customer.city}</strong></div>
            <div><span>Contacto</span><strong>{orden.customer.email} · {orden.customer.phone}</strong></div>
            <small>Por seguridad, el correo y el teléfono se muestran parcialmente ocultos.</small>
          </> : <>
            <h2>Tu pedido aparecerá aquí</h2>
            <small>Los estados posibles son confirmado, en preparación, entregado y cancelado.</small>
          </>}
        </aside>
      </div>
    </main>
  );
}

function Profile({ pedidos }: { pedidos: PedidoSesion[] }) {
  return (
    <main className="page profile-page">
      <div className="profile-head">
        <div className="profile-avatar" aria-hidden="true">TL</div>
        <div><span className="eyebrow">Mi cuenta</span><h1>Mis pedidos</h1><p>Pedidos realizados en esta sesión del navegador</p></div>
        <Enlace a={rutas.consultar()} className="secondary">Consultar otro pedido</Enlace>
      </div>
      <div className="profile-grid">
        <section>
          <div className="section-head"><div><h2>Historial</h2></div></div>
          {pedidos.length ? pedidos.map(o => (
            <article className="order-card" key={o.orderNumber}>
              <div><span>Pedido #{o.orderNumber}</span><strong>{ETIQUETA_ESTADO[o.status]}</strong></div>
              <p>Total: {cop(o.totalCop)}</p>
              {o.createdAt && <small>Registrado el {fechaLocal(o.createdAt)} · </small>}
              <Enlace a={rutas.consultar(o.orderNumber)}>Ver estado actual</Enlace>
            </article>
          )) : (
            <div className="empty"><Icon name="bag"/><h2>Aún no tienes pedidos en esta sesión</h2>
              <p>Si compraste antes, consulta tu pedido con el número y tu correo.</p>
              <Enlace a={rutas.consultar()} className="primary">Consultar un pedido</Enlace></div>
          )}
        </section>
        <aside className="profile-links">
          <h2>Accesos rápidos</h2>
          <Enlace a={rutas.favoritos}><Icon name="heart"/> Mis favoritos <Icon name="arrow"/></Enlace>
          <Enlace a={rutas.carrito}><Icon name="bag"/> Mi carrito <Icon name="arrow"/></Enlace>
          <Enlace a={rutas.consultar()}><Icon name="search"/> Consultar pedido <Icon name="arrow"/></Enlace>
        </aside>
      </div>
    </main>
  );
}

function SearchModal({ productos, close }: { productos: ProductSummaryResponse[]; close: () => void }) {
  const { ir } = useNavegacion();
  const [query, setQuery] = useState("");
  const matches = productos.filter(p =>
    `${p.name} ${p.categoryName}`.toLowerCase().includes(query.toLowerCase()));

  useEffect(() => {
    const alTeclear = (e: KeyboardEvent) => { if (e.key === "Escape") close(); };
    window.addEventListener("keydown", alTeclear);
    return () => window.removeEventListener("keydown", alTeclear);
  }, [close]);

  return (
    <div className="modal-backdrop" onMouseDown={close}>
      <section className="search-modal" role="dialog" aria-modal="true" aria-label="Buscar en TiendaLocal"
               onMouseDown={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={close} aria-label="Cerrar búsqueda"><Icon name="close"/></button>
        <span className="eyebrow">Buscar en TiendaLocal</span>
        <label className="search-field"><Icon name="search"/>
          <span className="sr-only">Buscar productos o categorías</span>
          <input autoFocus value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Busca productos o categorías"/>
        </label>
        {query && <div className="search-results" aria-live="polite">
          {matches.length ? matches.slice(0, 5).map(p => (
            <button key={p.id} onClick={() => { close(); ir(rutas.producto(p.slug)); }}>
              <Foto src={p.imageUrl} alt=""/>
              <span><strong>{p.name}</strong><small>{p.categoryName} · {cop(p.priceCop)}</small></span>
              <Icon name="arrow"/>
            </button>
          )) : <p>No encontramos resultados para “{query}”.</p>}
        </div>}
      </section>
    </div>
  );
}

function Footer() {
  const grupos: [string, [string, string][]][] = [
    ["Tienda", [["Catálogo", rutas.catalogo], ["Categorías", rutas.categorias], ["Artesanos", rutas.artesanos]]],
    ["Tu compra", [["Consultar pedido", rutas.consultar()], ["Carrito", rutas.carrito], ["Favoritos", rutas.favoritos]]],
    ["Negocio", [["Panel de administración", rutas.admin()], ["Vende con nosotros", rutas.ingresar()]]],
  ];
  return (
    <footer>
      <div className="footer-main">
        <div>
          <Enlace a={rutas.inicio} className="logo">Tienda<span>Local</span></Enlace>
          <p>Diseño independiente y artesanía contemporánea, directo de manos bogotanas.</p>
          <span>Bogotá, Colombia</span>
        </div>
        {grupos.map(([titulo, enlaces]) => (
          <nav key={titulo} aria-label={titulo}>
            <strong>{titulo}</strong>
            {enlaces.map(([texto, a]) => <Enlace key={texto} a={a}>{texto}</Enlace>)}
          </nav>
        ))}
      </div>
      <div className="footer-bottom">
        <span>© 2026 TiendaLocal</span>
        <span>Aviso: checkout simulado con fines académicos</span>
      </div>
    </footer>
  );
}

function Cargando({ titulo, texto }: { titulo: string; texto?: string }) {
  return <main className="page empty" style={{ minHeight: "60vh" }} aria-busy="true">
    <h2>{titulo}</h2>{texto && <p>{texto}</p>}</main>;
}

/* -------------------------------------------------------------- aplicación */

export default function App() {
  const [ubicacion, setUbicacion] = useState(direccionActual);
  const ruta = useMemo(() => leerRuta(ubicacion), [ubicacion]);

  const [productos, setProductos] = useState<ProductSummaryResponse[]>([]);
  const [categorias, setCategorias] = useState<CategoryResponse[]>([]);
  const [cargando, setCargando] = useState(true);
  const [fallo, setFallo] = useState<string | null>(null);
  const [saved, setSaved] = useGuardado<string[]>("local", "tl.favoritos", []);
  const [carrito, setCarrito] = useGuardado<ItemCarrito[]>("local", "tl.carrito", []);
  const [validacion, setValidacion] = useState<CartValidationResponse | null>(null);
  const [pedidos, setPedidos] = useGuardado<PedidoSesion[]>("session", "tl.pedidos", []);
  const [ultimaOrden, setUltimaOrden] = useState<OrderResponse | null>(null);
  const [detalle, setDetalle] = useState<ProductResponse | null>(null);
  const [detalleFallo, setDetalleFallo] = useState(false);
  const [searching, setSearching] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  /** Cambia de ruta y deja constancia en el historial, para que «atrás» y
   *  «adelante» funcionen y cualquier sección pueda recargarse o compartirse.
   *  `reemplazar` sirve cuando la ruta cambia sin que el usuario lo haya
   *  pedido —una redirección—: añadir una entrada ahí haría que «atrás»
   *  regresara a una dirección que redirige otra vez. */
  const ir: Ir = useCallback((destino, { reemplazar = false } = {}) => {
    if (destino !== direccionActual() || reemplazar) {
      window.history[reemplazar ? "replaceState" : "pushState"](null, "", destino);
    }
    setUbicacion(destino);
    window.scrollTo(0, 0);
  }, []);

  /* Atrás y adelante del navegador. */
  useEffect(() => {
    const alNavegar = () => setUbicacion(direccionActual());
    window.addEventListener("popstate", alNavegar);
    return () => window.removeEventListener("popstate", alNavegar);
  }, []);

  const cargar = useCallback(async (silencioso = false) => {
    if (!silencioso) setCargando(true);
    try {
      const [cats, prods] = await Promise.all([listarCategorias(), listarCatalogoCompleto()]);
      setCategorias(cats); setProductos(prods); setFallo(null);
    } catch (e) {
      setFallo(e instanceof Error ? e.message : "No se pudo cargar el catálogo.");
    } finally { if (!silencioso) setCargando(false); }
  }, []);

  useEffect(() => { void cargar(); }, [cargar]);

  useEffect(() => {
    if (!aviso) return;
    const t = window.setTimeout(() => setAviso(null), 2600);
    return () => window.clearTimeout(t);
  }, [aviso]);

  /* El panel exige sesión. El token vive en memoria y no sobrevive a una
     recarga: entrar directo a /admin/… lleva al formulario y, al iniciar
     sesión, de vuelta a la misma sección. `/admin` a secas se normaliza a
     su primera sección para que el menú marque cuál está abierta. */
  useEffect(() => {
    if (ruta.vista !== "admin") return;
    if (!haySesion()) ir(rutas.ingresar(ubicacion), { reemplazar: true });
    else if (ubicacion.split("?")[0].replace(/\/$/, "") === "/admin") ir(rutas.admin(), { reemplazar: true });
  }, [ruta, ubicacion, ir]);

  /* La confirmación de compra solo se muestra en /pago, justo después de
     pagar; al salir de ahí se descarta. */
  useEffect(() => { if (ruta.vista !== "checkout") setUltimaOrden(null); }, [ruta.vista]);

  /* Detalle de producto: se pide por slug cada vez que la ruta lo cambia,
     también al recargar o al volver con «atrás». */
  const slugProducto = ruta.vista === "product" ? ruta.slug : null;
  useEffect(() => {
    if (!slugProducto || detalle?.slug === slugProducto) return;
    let vigente = true;
    setDetalle(null); setDetalleFallo(false);
    obtenerProducto(slugProducto)
      .then(p => { if (vigente) setDetalle(p); })
      .catch(() => { if (vigente) setDetalleFallo(true); });
    return () => { vigente = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slugProducto]);

  /* EP-04. Al abrir el carrito o el pago se comprueba la disponibilidad
     contra el servidor: lo que el navegador recuerda puede llevar minutos
     desactualizado. No reserva unidades (RN-06). */
  const claveCarrito = carrito.map(i => `${i.variantId}:${i.quantity}`).join(",");
  const enCompra = ruta.vista === "cart" || ruta.vista === "checkout";
  useEffect(() => {
    if (!enCompra || !carrito.length) { setValidacion(null); return; }
    let vigente = true;
    validarCarrito(carrito.map(i => ({ variantId: i.variantId, quantity: i.quantity })))
      .then(v => {
        if (!vigente) return;
        setValidacion(v);
        setCarrito(items => items.map(i => {
          const l = v.items.find(x => x.variantId === i.variantId);
          return l ? { ...i, availableUnits: l.availableUnits, unitPriceCop: l.unitPriceCop } : i;
        }));
      })
      .catch(() => { if (vigente) setValidacion(null); });
    return () => { vigente = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [claveCarrito, enCompra]);

  const categoriaActual = ruta.vista === "category"
    ? categorias.find(c => c.slug === ruta.slug) ?? null : null;

  /* Un producto o una categoría inexistentes se titulan como lo que muestran:
     «Página no encontrada», no «Producto». La categoría solo se da por
     inexistente cuando el catálogo ya cargó. */
  const inexistente = (ruta.vista === "product" && detalleFallo)
    || (ruta.vista === "category" && !cargando && !fallo && !categoriaActual);
  useEffect(() => {
    document.title = tituloDe(inexistente ? { vista: "notFound" } : ruta,
      { categoria: categoriaActual?.name, producto: detalle?.name });
  }, [ruta, inexistente, categoriaActual?.name, detalle?.name]);

  const toggle = (id: string) =>
    setSaved(x => x.includes(id) ? x.filter(y => y !== id) : [...x, id]);

  const agregarVariante = (p: ProductResponse, v: ProductVariantResponse, cantidad = 1) => {
    setCarrito(items => {
      const existente = items.find(i => i.variantId === v.id);
      const total = Math.min((existente?.quantity ?? 0) + cantidad, v.availableUnits);
      if (existente) return items.map(i => i.variantId === v.id ? { ...i, quantity: total } : i);
      return [...items, {
        variantId: v.id, productSlug: p.slug, productName: p.name,
        categoryName: p.category.name, size: v.size, unitPriceCop: p.priceCop,
        imageUrl: p.images[0]?.url ?? p.imageUrl, imageAlt: p.images[0]?.alt ?? p.imageAlt,
        quantity: total, availableUnits: v.availableUnits,
      }];
    });
    setAviso(`${p.name} (talla ${v.size}) se agregó al carrito`);
  };

  /** Desde una tarjeta hace falta el detalle, porque solo él trae las
      variantes con identificador. Si hay una sola disponible, la agrega;
      si hay varias, abre el detalle para elegir talla. */
  const agregarRapido = async (p: ProductSummaryResponse) => {
    if (!p.inStock) { setAviso(`${p.name} no tiene existencias`); return; }
    try {
      const completo = await obtenerProducto(p.slug);
      const disponibles = completo.variants.filter(v => v.inStock);
      if (disponibles.length === 1) { agregarVariante(completo, disponibles[0]); return; }
      setDetalle(completo);
      ir(rutas.producto(p.slug));
      setAviso("Elige una talla para agregarlo al carrito");
    } catch (e) {
      setAviso(e instanceof Error ? e.message : "No se pudo agregar el producto");
    }
  };

  const cambiarCantidad = (variantId: string, cantidad: number) => {
    setCarrito(items => cantidad <= 0
      ? items.filter(i => i.variantId !== variantId)
      : items.map(i => i.variantId === variantId
          ? { ...i, quantity: Math.min(cantidad, i.availableUnits) } : i));
  };
  const quitar = (variantId: string) =>
    setCarrito(items => items.filter(i => i.variantId !== variantId));

  const confirmarPedido = async (cliente: CustomerRequest, consentimiento: boolean) => {
    const orden = await crearOrden(
      carrito.map(i => ({ variantId: i.variantId, quantity: i.quantity })),
      cliente, consentimiento);
    setPedidos(p => [{ orderNumber: orden.orderNumber, status: orden.status,
                       totalCop: orden.totalCop, createdAt: orden.createdAt }, ...p]);
    setUltimaOrden(orden);
    setCarrito([]);
    // Refresco silencioso: recarga existencias sin desmontar la vista,
    // que es lo que borraría la confirmación que el comprador debe ver.
    void cargar(true);
    return orden;
  };

  const entrarAdmin = async (email: string, clave: string) => {
    await iniciarSesion(email, clave);
    ir(ruta.vista === "login" && ruta.volver ? ruta.volver : rutas.admin());
  };

  const salirAdmin = () => { cerrarSesion(); ir(rutas.inicio); };

  const acciones: Acciones = { saved, toggle, add: p => void agregarRapido(p) };
  const unidades = carrito.reduce((s, i) => s + i.quantity, 0);
  const navegacion = { ubicacion, ir };

  const envolver = (contenido: ReactNode) =>
    <ContextoNavegacion.Provider value={navegacion}>{contenido}</ContextoNavegacion.Provider>;

  if (ruta.vista === "login") {
    return envolver(<Login volver={ruta.volver} entrarAdmin={entrarAdmin}/>);
  }
  if (ruta.vista === "admin") {
    return envolver(haySesion() ? <Admin ruta={ruta} salir={salirAdmin}/> : null);
  }

  let pagina: ReactNode;
  const necesitaCatalogo = !["cart", "checkout", "profile", "lookup", "notFound"].includes(ruta.vista);
  if (necesitaCatalogo && cargando) {
    pagina = <Cargando titulo="Cargando catálogo…" texto="Consultando el inventario disponible."/>;
  } else if (necesitaCatalogo && fallo) {
    pagina = <main className="page empty" style={{ minHeight: "60vh" }}>
      <h2>No pudimos cargar el catálogo</h2>
      <p>{fallo}</p>
      <button className="primary" onClick={() => void cargar()}>Reintentar</button>
    </main>;
  } else {
    switch (ruta.vista) {
      case "home":
        pagina = <Home productos={productos} categorias={categorias} acciones={acciones}/>; break;
      case "catalog":
        pagina = <Catalogo productos={productos} categorias={categorias} acciones={acciones}/>; break;
      case "categories":
        pagina = <Categorias categorias={categorias}/>; break;
      case "category":
        pagina = categoriaActual
          ? <Categoria categoria={categoriaActual} indice={categorias.indexOf(categoriaActual)} productos={productos} acciones={acciones}/>
          : <NoEncontrada mensaje="Esa categoría no existe."/>;
        break;
      case "artisans":
        pagina = <Artesanos productos={productos} categorias={categorias} acciones={acciones}/>; break;
      case "product":
        if (detalleFallo) { pagina = <NoEncontrada mensaje="Este producto no existe o ya no está disponible."/>; break; }
        pagina = detalle && detalle.slug === ruta.slug
          ? <ProductDetail producto={detalle}
              relacionados={productos.filter(p => p.categoryName === detalle.category.name && p.id !== detalle.id).slice(0, 3)}
              saved={saved.includes(detalle.id)} toggle={() => toggle(detalle.id)}
              agregar={agregarVariante} acciones={acciones}/>
          : <Cargando titulo="Cargando producto…"/>;
        break;
      case "favorites":
        pagina = <Favorites productos={productos} acciones={acciones}/>; break;
      case "cart":
        pagina = <Cart items={carrito} validacion={validacion} cambiar={cambiarCantidad} quitar={quitar}/>; break;
      case "checkout":
        pagina = <Checkout items={carrito} orden={ultimaOrden} confirmar={confirmarPedido}/>; break;
      case "profile":
        pagina = <Profile pedidos={pedidos}/>; break;
      case "lookup":
        pagina = <ConsultarPedido key={ruta.numero} numeroInicial={ruta.numero}/>; break;
      default:
        pagina = <NoEncontrada/>;
    }
  }

  return envolver(<>
    <a className="saltar" href="#contenido">Saltar al contenido</a>
    <Header search={() => setSearching(true)} favCount={saved.length} cartCount={unidades}/>
    <div id="contenido" tabIndex={-1}>{pagina}</div>
    <Footer/>
    {searching && <SearchModal productos={productos} close={() => setSearching(false)}/>}
    {aviso && <div className="toast" role="status">{aviso}</div>}
  </>);
}
