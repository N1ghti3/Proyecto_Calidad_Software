import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ApiError, AVISO_PRIVACIDAD, ajustarInventario, cerrarSesion, cop, crearOrden,
  fechaLocal, iniciarSesion, listarCatalogoCompleto, listarCategorias,
  obtenerInventario, obtenerOrdenesAdmin, obtenerProducto,
  type CategoryResponse, type CustomerRequest, type InventoryResponse,
  type OrderResponse, type OrderSummaryResponse, type ProductResponse,
  type ProductSummaryResponse, type ProductVariantResponse,
} from "./api";

type View = "home" | "product" | "favorites" | "cart" | "checkout" | "profile" | "login" | "admin";

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
  "Camisetas":    { image: photos.tee,    subtitle: "Básicos gráficos de edición local" },
  "Bolsos":       { image: photos.woven,  subtitle: "Tejidos, cuero y fibras naturales" },
  "Joyería":      { image: photos.jewels, subtitle: "Piezas pequeñas hechas a mano" },
  "Calzado":      { image: photos.shoe,   subtitle: "Diseño cómodo para recorrer la ciudad" },
  "Hogar & arte": { image: photos.basket, subtitle: "Objetos con oficio y memoria" },
};

/** Imagen que degrada sin romperse cuando el archivo no existe.
 *
 * El catálogo guarda rutas de fotografía (`/media/productos/…`) aunque el
 * archivo todavía no se haya subido. Un `<img>` corriente muestra entonces el
 * ícono de imagen rota con el texto alternativo desbordando la tarjeta, que es
 * peor que no mostrar nada: parece un fallo del sistema cuando en realidad es
 * contenido que falta.
 *
 * Al fallar la carga se retira la imagen y queda el bloque de color del
 * contenedor, que el diseño ya usa como fondo. La descripción no se pierde:
 * pasa a `aria-label`, de modo que sigue disponible para lectores de pantalla
 * (RNF-03) sin ocupar espacio visual.
 */
function Foto({ src, alt, className, onClick, loading }: {
  src: string | null | undefined;
  alt: string;
  className?: string;
  onClick?: () => void;
  loading?: "lazy" | "eager";
}) {
  const [falló, setFalló] = useState(false);
  useEffect(() => { setFalló(false); }, [src]);

  if (!src || falló) {
    return (
      <span className={`foto-ausente ${className ?? ""}`} role="img" aria-label={alt}
            onClick={onClick} />
    );
  }
  return (
    <img src={src} alt={alt} className={className} onClick={onClick} loading={loading}
         onError={() => setFalló(true)} />
  );
}

const anclaCategoria = (slug: string) => `cat-${slug}`;
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

function Icon({ name, filled = false }: { name: string; filled?: boolean }) {
  const paths: Record<string, React.ReactNode> = {
    search: <><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/></>,
    heart: <path d="M20.8 4.7a5.5 5.5 0 0 0-7.8 0L12 5.8l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8l1.1 1.1L12 21l7.8-7.4 1.1-1.1a5.5 5.5 0 0 0-.1-7.8Z"/>,
    bag: <><path d="M5 8h14l-1 13H6L5 8Z"/><path d="M9 9V6a3 3 0 0 1 6 0v3"/></>,
    user: <><circle cx="12" cy="8" r="4"/><path d="M4.5 21a7.5 7.5 0 0 1 15 0"/></>,
    arrow: <><path d="M5 12h14"/><path d="m14 7 5 5-5 5"/></>,
    truck: <><path d="M3 6h11v11H3z"/><path d="M14 10h4l3 3v4h-7z"/><circle cx="7" cy="19" r="2"/><circle cx="18" cy="19" r="2"/></>,
    refresh: <><path d="M20 7v5h-5"/><path d="M18.5 15A7 7 0 1 1 17 6l3 6"/></>,
    message: <path d="M21 12a8 8 0 0 1-8 8H5l-3 2 1-6a9 9 0 1 1 18-4Z"/>,
    menu: <><path d="M4 7h16M4 12h16M4 17h16"/></>,
    close: <path d="m6 6 12 12M18 6 6 18"/>,
    eye: <><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="2.5"/></>,
    minus: <path d="M5 12h14"/>,
    plus: <path d="M12 5v14M5 12h14"/>,
    trash: <><path d="M4 7h16M9 7V4h6v3m3 0-1 14H7L6 7"/><path d="M10 11v6M14 11v6"/></>,
    grid: <><rect x="4" y="4" width="6" height="6"/><rect x="14" y="4" width="6" height="6"/><rect x="4" y="14" width="6" height="6"/><rect x="14" y="14" width="6" height="6"/></>,
    chart: <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
  };
  return <svg aria-hidden="true" className="icon" viewBox="0 0 24 24" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

function Header({ go, goSection, search, favCount, cartCount }: {
  go: (v: View) => void; goSection: (id: string) => void; search: () => void;
  favCount: number; cartCount: number;
}) {
  const [open, setOpen] = useState(false);
  const navigate = (action: () => void) => { action(); setOpen(false); };
  return (
    <header className="header">
      <button className="logo" onClick={() => go("home")}>Tienda<span>Local</span></button>
      <nav className={open ? "nav open" : "nav"}>
        <button onClick={() => navigate(() => go("home"))}>Inicio</button>
        <button onClick={() => navigate(() => goSection("catalogo"))}>Catálogo</button>
        <button onClick={() => navigate(() => goSection("categorias"))}>Categorías</button>
        <button onClick={() => navigate(() => goSection("artesanos"))}>Artesanos</button>
      </nav>
      <div className="header-actions">
        <button className="icon-btn search-btn" aria-label="Buscar" onClick={search}><Icon name="search"/></button>
        <button className="icon-btn" aria-label="Favoritos" onClick={() => go("favorites")}><Icon name="heart"/>{favCount > 0 && <b>{favCount}</b>}</button>
        <button className="icon-btn" aria-label="Carrito" onClick={() => go("cart")}><Icon name="bag"/>{cartCount > 0 && <b>{cartCount}</b>}</button>
        <button className="icon-btn" aria-label="Cuenta" onClick={() => go("profile")}><Icon name="user"/></button>
        <button className="icon-btn menu-btn" aria-label="Menú" onClick={() => setOpen(!open)}><Icon name={open ? "close" : "menu"}/></button>
      </div>
    </header>
  );
}

function ProductCard({ product, saved, toggle, add, open }: {
  product: ProductSummaryResponse; saved: boolean;
  toggle: () => void; add: () => void; open: () => void;
}) {
  const marca = insignia(product);
  return (
    <article className="product-card">
      <div className={`product-image ${tono(product.id)}`}>
        <Foto src={product.imageUrl} alt={product.imageAlt ?? product.name}
              onClick={open} loading="lazy"/>
        {marca && <span className={marca.verde ? "badge green" : "badge"}>{marca.texto}</span>}
        <button className={`heart ${saved ? "saved" : ""}`} onClick={toggle}
                aria-label={saved ? `Quitar ${product.name} de favoritos` : `Guardar ${product.name} en favoritos`}>
          <Icon name="heart" filled={saved}/>
        </button>
        <button className="quick-add" onClick={add} disabled={!product.inStock}>
          {product.inStock ? <>Agregar al carrito <Icon name="plus"/></> : "Sin existencias"}
        </button>
      </div>
      <button className="product-copy" onClick={open}>
        <span>{product.categoryName}</span>
        <strong>{product.name}</strong>
        <div><em>{cop(product.priceCop)}</em><small>{product.availableUnits} disponibles</small></div>
      </button>
    </article>
  );
}

function Home({ productos, categorias, saved, toggle, add, abrir, go }: {
  productos: ProductSummaryResponse[]; categorias: CategoryResponse[]; saved: string[];
  toggle: (id: string) => void; add: (p: ProductSummaryResponse) => void;
  abrir: (p: ProductSummaryResponse) => void; go: (v: View) => void;
}) {
  const nuevos = productos.slice(0, 4);
  const masVendidos = useMemo(
    () => [...productos].sort((a, b) => b.availableUnits - a.availableUnits).slice(0, 4),
    [productos],
  );
  const total = productos.length;

  const section = (title: string, items: ProductSummaryResponse[], id?: string) => (
    <section className="section" id={id}>
      <div className="section-head">
        <div><span className="eyebrow">Selección local</span><h2>{title}</h2></div>
        <button onClick={() => document.getElementById("catalogo")?.scrollIntoView({ behavior: "smooth" })}>Ver todo <Icon name="arrow"/></button>
      </div>
      <div className="product-grid">
        {items.map(p => <ProductCard key={p.id} product={p} saved={saved.includes(p.id)}
          toggle={() => toggle(p.id)} add={() => add(p)} open={() => abrir(p)}/>)}
      </div>
    </section>
  );

  return (
    <>
      <main>
        <section className="hero">
          <div className="hero-copy">
            <span className="kicker">Colección nueva · Hecho en Bogotá</span>
            <h1>Descubre piezas que <i>no vas a encontrar</i> en otro lado.</h1>
            <p>Moda urbana y artesanías directo del taller a tu puerta, con disponibilidad real.</p>
            <div className="hero-actions">
              <button className="primary" onClick={() => document.getElementById("nuevos")?.scrollIntoView({ behavior: "smooth" })}>Ver catálogo <Icon name="arrow"/></button>
              <button className="secondary" onClick={() => document.getElementById("artesanos")?.scrollIntoView({ behavior: "smooth" })}>Conocer artesanos</button>
            </div>
          </div>
          <div className="hero-visual">
            <div className="shape"></div><img src={photos.hero} alt="Moda urbana de nueva colección"/>
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

        <section className="categories section" id="categorias">
          <div className="section-head">
            <div><span className="eyebrow">Encuentra tu estilo</span><h2>Comprar por categoría</h2></div>
            <p className="catalog-count">{total} piezas · {categorias.length} colecciones</p>
          </div>
          <div className="category-row">
            {categorias.map((c, i) => (
              <button key={c.id} onClick={() => document.getElementById(anclaCategoria(c.slug))?.scrollIntoView({ behavior: "smooth" })}>
                <span><img src={portadas[c.name]?.image ?? photos.hero} alt={c.name}/><b>0{i + 1}</b></span>
                <strong>{c.name}</strong><small>{c.productCount} productos</small>
              </button>
            ))}
          </div>
        </section>

        <div id="nuevos">{section("Nuevos ingresos", nuevos)}</div>
        {section("Los más vendidos", masVendidos)}

        <section className="catalog-intro section" id="catalogo">
          <span className="eyebrow">Catálogo completo</span>
          <div>
            <h2>Más diseño local,<br/>más formas de encontrar tu estilo.</h2>
            <p>Explora {total} piezas creadas por talleres independientes de Bogotá. Cada colección reúne materiales, oficios y miradas diferentes.</p>
          </div>
          <nav aria-label="Categorías del catálogo">
            {categorias.map(c => (
              <button key={c.id} onClick={() => document.getElementById(anclaCategoria(c.slug))?.scrollIntoView({ behavior: "smooth" })}>
                {c.name}<span>{c.productCount}</span>
              </button>
            ))}
          </nav>
        </section>

        <div className="category-catalog">
          {categorias.map((c, index) => {
            const items = productos.filter(p => p.categoryName === c.name);
            if (!items.length) return null;
            return (
              <section className="category-shelf section" id={anclaCategoria(c.slug)} key={c.id}>
                <div className="category-title">
                  <span>0{index + 1}</span>
                  <div><h2>{c.name}</h2><p>{portadas[c.name]?.subtitle ?? "Piezas de talleres locales"}</p></div>
                  <small>{items.length} productos</small>
                </div>
                <div className="product-grid">
                  {items.map(p => <ProductCard key={p.id} product={p} saved={saved.includes(p.id)}
                    toggle={() => toggle(p.id)} add={() => add(p)} open={() => abrir(p)}/>)}
                </div>
              </section>
            );
          })}
        </div>

        <section className="promos section" id="artesanos">
          <article className="promo orange">
            <span>Solo esta semana</span><h2>Hasta 30% en accesorios</h2>
            <button onClick={() => document.getElementById("nuevos")?.scrollIntoView({ behavior: "smooth" })}>Comprar ahora <Icon name="arrow"/></button>
          </article>
          <article className="promo dark">
            <span>Edición limitada</span><h2>Piezas artesanales de temporada</h2>
            <button onClick={() => productos[0] && abrir(productos[0])}>Descubrir <Icon name="arrow"/></button>
          </article>
        </section>
      </main>
      <Footer go={go}/>
    </>
  );
}

function Field({ label, placeholder, type = "text", name, required = false, pattern, title }: {
  label: string; placeholder: string; type?: string; name?: string;
  required?: boolean; pattern?: string; title?: string;
}) {
  return (
    <label className="field"><span>{label}</span>
      <input type={type} name={name} placeholder={placeholder} required={required}
             pattern={pattern} title={title}/>
    </label>
  );
}

function Login({ close, entrarAdmin, irPerfil }: {
  close: () => void; entrarAdmin: (email: string, clave: string) => Promise<void>; irPerfil: () => void;
}) {
  const [role, setRole] = useState<"client" | "admin">("client");
  const [create, setCreate] = useState(false);
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const selectRole = (next: "client" | "admin") => {
    setRole(next); setError(null); if (next === "admin") setCreate(false);
  };

  const enviar = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (role === "client") { irPerfil(); return; }
    setError(null); setEnviando(true);
    const datos = new FormData(e.currentTarget);
    try {
      await entrarAdmin(String(datos.get("email") || ""), String(datos.get("password") || ""));
    } catch (err) {
      setError(err instanceof ApiError && err.code === "INVALID_CREDENTIALS"
        ? "Correo o contraseña incorrectos."
        : err instanceof Error ? err.message : "No se pudo iniciar sesión.");
    } finally { setEnviando(false); }
  };

  return (
    <div className={`login-page ${role === "admin" ? "admin-mode" : ""}`}>
      <button className="back-home" onClick={close}><Icon name="arrow"/> Volver a la tienda</button>
      <div className="login-art">
        <button className="logo" onClick={close}>Tienda<span>Local</span></button>
        <div><span className="kicker">Compra local. Viste diferente.</span><h2>Diseño con origen,<br/>historias con futuro.</h2><p>Conectamos el talento independiente de Bogotá con personas que valoran lo auténtico.</p></div>
        <small>Hecho por manos locales — Bogotá, Colombia</small>
      </div>
      <section className="login-card">
        <div className="login-title"><span>TL</span><h1>Bienvenido a TiendaLocal</h1><p>Ingresa para guardar tus favoritos y seguir tus pedidos.</p></div>
        <div className="role-switch">
          <button className={role === "client" ? "active" : ""} onClick={() => selectRole("client")}>Cliente</button>
          <button className={role === "admin" ? "active" : ""} onClick={() => selectRole("admin")}>Administrador</button>
        </div>
        {role === "client" && <div className="mode-switch">
          <button className={!create ? "active" : ""} onClick={() => setCreate(false)}>Iniciar sesión</button>
          <button className={create ? "active" : ""} onClick={() => setCreate(true)}>Crear cuenta</button>
        </div>}
        <form onSubmit={enviar}>
          {create && <Field label="Nombre completo" placeholder="Tu nombre y apellido"/>}
          <Field label={role === "admin" ? "Correo electrónico del negocio" : "Correo electrónico"}
                 placeholder={role === "admin" ? "hola@tunegocio.co" : "nombre@correo.com"}
                 type="email" name="email" required/>
          {create && <Field label="Teléfono" placeholder="+57 300 000 0000"/>}
          <label className="field"><span>Contraseña</span>
            <div><input type={show ? "text" : "password"} name="password"
                        placeholder="Mínimo 8 caracteres" required={role === "admin"}/>
              <button type="button" onClick={() => setShow(!show)} aria-label="Mostrar u ocultar contraseña"><Icon name="eye"/></button></div>
          </label>
          {create && <Field label="Confirmar contraseña" placeholder="Repite tu contraseña" type="password"/>}
          {!create && role === "client" && <button type="button" className="forgot" onClick={() => window.alert("Te enviaremos instrucciones para recuperar tu contraseña.")}>¿Olvidaste tu contraseña?</button>}
          {create && <label className="check"><input type="checkbox"/> <span>Autorizo el tratamiento de mis datos personales y acepto la <u>Política de privacidad</u>.</span></label>}
          {error && <div className="stock-warning" role="alert">{error}</div>}
          <button className="submit" type="submit" disabled={enviando}>
            {enviando ? "Entrando…" : role === "admin" ? "Entrar al panel" : create ? "Crear mi cuenta" : "Iniciar sesión"} <Icon name="arrow"/>
          </button>
        </form>
        {!create && role === "client" && <>
          <div className="or"><span>o continúa con</span></div>
          <button className="google" onClick={irPerfil}><b>G</b> Continuar con Google</button>
          <p className="signup">¿No tienes cuenta? <button onClick={() => setCreate(true)}>Crear cuenta</button></p>
        </>}
        {role === "admin" && <div className="admin-note"><Icon name="grid"/><span><strong>Acceso exclusivo para negocios</strong>Gestiona catálogo, inventario y pedidos. Si vas a comprar, usa la pestaña Cliente.</span></div>}
      </section>
    </div>
  );
}

function ProductDetail({ producto, cargando, relacionados, saved, toggle, agregar, abrir, go }: {
  producto: ProductResponse | null; cargando: boolean;
  relacionados: ProductSummaryResponse[]; saved: boolean; toggle: () => void;
  agregar: (p: ProductResponse, v: ProductVariantResponse, cantidad: number) => void;
  abrir: (p: ProductSummaryResponse) => void; go: (v: View) => void;
}) {
  const [variantId, setVariantId] = useState<string | null>(null);
  const [qty, setQty] = useState(1);

  useEffect(() => {
    const primera = producto?.variants.find(v => v.inStock);
    setVariantId(primera?.id ?? null);
    setQty(1);
  }, [producto?.id]);

  if (cargando || !producto) {
    return <main className="page empty" style={{ minHeight: "50vh" }}>
      <h2>Cargando producto…</h2></main>;
  }

  const variante = producto.variants.find(v => v.id === variantId) ?? null;
  const maximo = variante?.availableUnits ?? 0;
  const imagenPrincipal = producto.images[0]?.url ?? producto.imageUrl;
  const altPrincipal = producto.images[0]?.alt ?? producto.imageAlt ?? producto.name;

  return (
    <main className="detail page">
      <button className="breadcrumb" onClick={() => go("home")}>Inicio / {producto.category.name} / <b>{producto.name}</b></button>
      <div className="detail-grid">
        <div className="gallery">
          <div className="main-photo"><Foto src={imagenPrincipal} alt={altPrincipal}/></div>
          {producto.images.length > 1 && (
            <div className="thumbs">
              {producto.images.map(img => (
                <button key={img.id} onClick={() => { /* galería: imagen principal fija por ahora */ }}>
                  <Foto src={img.url} alt={img.alt ?? producto.name}/>
                </button>
              ))}
            </div>
          )}
        </div>
        <section className="product-info">
          <span className="eyebrow">{producto.category.name} · {producto.variants[0]?.sku ?? producto.slug}</span>
          <h1>{producto.name}</h1>
          <p className="detail-price">{cop(producto.priceCop)} <small>IVA incluido</small></p>
          <p className="stock">
            {producto.inStock
              ? `● Disponible — ${producto.availableUnits} unidades`
              : "● Sin existencias por el momento"}
          </p>
          {producto.description && <p className="intro">{producto.description}</p>}

          <div className="options">
            <div><strong>{producto.variants.length > 1 ? "Selecciona tu talla" : "Presentación"}</strong></div>
            <div className="chips">
              {producto.variants.map(v => (
                <button key={v.id}
                        className={variantId === v.id ? "active" : ""}
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
              <span>{qty}</span>
              <button onClick={() => setQty(Math.min(maximo, qty + 1))} aria-label="Agregar una unidad" disabled={qty >= maximo}><Icon name="plus"/></button>
            </div>
            <button className="primary" disabled={!variante || maximo === 0}
                    onClick={() => variante && agregar(producto, variante, qty)}>
              {maximo === 0 ? "Sin existencias" : <>Agregar al carrito <Icon name="bag"/></>}
            </button>
            <button className={`detail-heart ${saved ? "saved" : ""}`} onClick={toggle}
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
          <div className="product-grid">
            {relacionados.map(p => <ProductCard key={p.id} product={p} saved={false}
              toggle={() => {}} add={() => abrir(p)}
              open={() => { abrir(p); window.scrollTo({ top: 0, behavior: "smooth" }); }}/>)}
          </div>
        </section>
      )}
    </main>
  );
}

function Favorites({ productos, ids, toggle, add, abrir, go }: {
  productos: ProductSummaryResponse[]; ids: string[]; toggle: (id: string) => void;
  add: (p: ProductSummaryResponse) => void; abrir: (p: ProductSummaryResponse) => void; go: (v: View) => void;
}) {
  const all = productos.filter(p => ids.includes(p.id));
  return (
    <main className="page collection-page">
      <span className="eyebrow">Tu selección</span>
      <h1>Mis favoritos</h1>
      <p>{all.length} productos guardados</p>
      {all.length ? (
        <div className="product-grid">
          {all.map(p => <ProductCard key={p.id} product={p} saved toggle={() => toggle(p.id)} add={() => add(p)} open={() => abrir(p)}/>)}
        </div>
      ) : (
        <div className="empty"><Icon name="heart"/><h2>Aún no has guardado productos</h2>
          <p>Marca con el corazón las piezas que no quieres perder de vista.</p>
          <button className="primary" onClick={() => go("home")}>Explorar catálogo</button></div>
      )}
    </main>
  );
}

function Cart({ items, cambiar, quitar, go }: {
  items: ItemCarrito[]; cambiar: (variantId: string, cantidad: number) => void;
  quitar: (variantId: string) => void; go: (v: View) => void;
}) {
  const subtotal = items.reduce((s, i) => s + i.unitPriceCop * i.quantity, 0);
  return (
    <main className="page cart-page">
      <span className="eyebrow">Tu compra</span>
      <h1>Carrito <small>({items.reduce((s, i) => s + i.quantity, 0)} productos)</small></h1>
      <div className="cart-layout">
        <section className="cart-list">
          {items.length ? items.map(item => (
            <article className="cart-item" key={item.variantId}>
              <Foto src={item.imageUrl} alt={item.imageAlt ?? item.productName}/>
              <div>
                <span>{item.categoryName}</span>
                <h3>{item.productName}</h3>
                <p>Talla: {item.size}</p>
                <div className="stepper">
                  <button onClick={() => cambiar(item.variantId, item.quantity - 1)} aria-label="Quitar una unidad"><Icon name="minus"/></button>
                  <span>{item.quantity}</span>
                  <button onClick={() => cambiar(item.variantId, item.quantity + 1)} aria-label="Agregar una unidad" disabled={item.quantity >= item.availableUnits}><Icon name="plus"/></button>
                </div>
                {item.quantity >= item.availableUnits && <p className="stock-warning">Solo quedan {item.availableUnits} unidades disponibles</p>}
              </div>
              <strong>{cop(item.unitPriceCop * item.quantity)}</strong>
              <button className="remove" onClick={() => quitar(item.variantId)} aria-label={`Eliminar ${item.productName}`}><Icon name="trash"/></button>
            </article>
          )) : (
            <div className="empty"><Icon name="bag"/><h2>Tu carrito está vacío</h2>
              <button className="primary" onClick={() => go("home")}>Explorar catálogo</button></div>
          )}
        </section>
        <aside className="summary">
          <h2>Resumen de compra</h2>
          <div><span>Subtotal</span><strong>{cop(subtotal)}</strong></div>
          <div><span>Envío</span><strong>Calculado al pagar</strong></div>
          <hr/>
          <div className="total"><span>Total</span><strong>{cop(subtotal)}</strong></div>
          <button className="primary" disabled={!items.length} onClick={() => go("checkout")}>Continuar al pago <Icon name="arrow"/></button>
          <small>Pago seguro · Checkout simulado con fines académicos</small>
        </aside>
      </div>
    </main>
  );
}

function Checkout({ items, orden, confirmar, go }: {
  items: ItemCarrito[];
  orden: OrderResponse | null;
  confirmar: (cliente: CustomerRequest, consentimiento: boolean) => Promise<OrderResponse>;
  go: (v: View) => void;
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
          <button className="primary" onClick={() => go("profile")}>Ver mis pedidos <Icon name="arrow"/></button>
        </div>
      </main>
    );
  }

  const enviar = async (e: React.FormEvent<HTMLFormElement>) => {
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
      <button className="breadcrumb" onClick={() => go("cart")}>← Volver al carrito</button>
      <span className="eyebrow">Pago seguro</span>
      <h1>Finaliza tu compra</h1>
      <div className="checkout-layout">
        <form className="checkout-form" onSubmit={enviar}>
          <section>
            <h2>Datos de entrega</h2>
            <div className="form-row">
              <Field label="Nombre completo" placeholder="Ana Ríos" name="name" required/>
              <Field label="Correo electrónico" placeholder="ana@correo.com" type="email" name="email" required/>
            </div>
            <div className="form-row">
              <Field label="Teléfono" placeholder="+57 300 000 0000" name="phone" required
                     pattern="^\+?[0-9]{7,15}$"
                     title="Entre 7 y 15 dígitos, con + opcional al inicio"/>
              <Field label="Ciudad" placeholder="Bogotá D.C." name="city" required/>
            </div>
            <Field label="Dirección" placeholder="Calle 45 # 12-34, apto 201" name="address" required/>
          </section>
          <section>
            <h2>Método de pago</h2>
            <label className="payment-option"><input type="radio" name="payment" defaultChecked/>
              <span><strong>Pago contra entrega</strong><small>Paga en efectivo o transferencia al recibir.</small></span></label>
            <label className="payment-option"><input type="radio" name="payment"/>
              <span><strong>Tarjeta de prueba</strong><small>Checkout simulado; no se realizará ningún cobro.</small></span></label>
          </section>
          {/* RN-16 · Ley 1581 de 2012: sin consentimiento el servidor responde CONSENT_REQUIRED. */}
          <label className="check"><input type="checkbox" name="consent" required/>
            <span>Autorizo el tratamiento de mis datos personales con la única finalidad de
                  gestionar y entregar este pedido (aviso de privacidad v{AVISO_PRIVACIDAD}).</span></label>
          {error && <div className="stock-warning" role="alert">
            <strong>{error}</strong>
            {faltantes.length > 0 && <ul>{faltantes.map(f => <li key={f}>{f}</li>)}</ul>}
          </div>}
          <button className="primary" type="submit" disabled={enviando || !items.length}>
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

function Profile({ pedidos, go }: { pedidos: OrderResponse[]; go: (v: View) => void }) {
  return (
    <main className="page profile-page">
      <div className="profile-head">
        <div className="profile-avatar">TL</div>
        <div><span className="eyebrow">Mi cuenta</span><h1>Mis pedidos</h1><p>Pedidos realizados en esta sesión</p></div>
        <button className="secondary" onClick={() => go("login")}>Cambiar cuenta</button>
      </div>
      <div className="profile-grid">
        <section>
          <div className="section-head"><div><h2>Historial</h2></div></div>
          {pedidos.length ? pedidos.map(o => (
            <article className="order-card" key={o.orderNumber}>
              <div><span>Pedido #{o.orderNumber}</span><strong>{o.status}</strong></div>
              <p>Total: {cop(o.totalCop)}</p>
              {o.createdAt && <small>Registrado el {fechaLocal(o.createdAt)}</small>}
            </article>
          )) : (
            <div className="empty"><Icon name="bag"/><h2>Aún no tienes pedidos</h2>
              <button className="primary" onClick={() => go("home")}>Explorar catálogo</button></div>
          )}
        </section>
        <aside className="profile-links">
          <h2>Accesos rápidos</h2>
          <button onClick={() => go("favorites")}><Icon name="heart"/> Mis favoritos <Icon name="arrow"/></button>
          <button onClick={() => go("cart")}><Icon name="bag"/> Mi carrito <Icon name="arrow"/></button>
        </aside>
      </div>
    </main>
  );
}

function SearchModal({ productos, close, abrir }: {
  productos: ProductSummaryResponse[]; close: () => void; abrir: (p: ProductSummaryResponse) => void;
}) {
  const [query, setQuery] = useState("");
  const matches = productos.filter(p =>
    `${p.name} ${p.categoryName}`.toLowerCase().includes(query.toLowerCase()));
  return (
    <div className="modal-backdrop" onMouseDown={close}>
      <section className="search-modal" onMouseDown={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={close} aria-label="Cerrar búsqueda"><Icon name="close"/></button>
        <span className="eyebrow">Buscar en TiendaLocal</span>
        <label className="search-field"><Icon name="search"/>
          <input autoFocus value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Busca productos o categorías"/>
        </label>
        {query && <div className="search-results">
          {matches.length ? matches.slice(0, 5).map(p => (
            <button key={p.id} onClick={() => { abrir(p); close(); }}>
              <Foto src={p.imageUrl} alt={p.imageAlt ?? p.name}/>
              <span><strong>{p.name}</strong><small>{p.categoryName} · {cop(p.priceCop)}</small></span>
              <Icon name="arrow"/>
            </button>
          )) : <p>No encontramos resultados para “{query}”.</p>}
        </div>}
      </section>
    </div>
  );
}

function Admin({ exit }: { exit: () => void }) {
  const [tab, setTab] = useState("Inventario");
  const [inventario, setInventario] = useState<InventoryResponse[]>([]);
  const [ordenes, setOrdenes] = useState<OrderSummaryResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);

  const recargar = useCallback(async () => {
    setCargando(true);
    try {
      const [inv, ord] = await Promise.all([obtenerInventario(), obtenerOrdenesAdmin()]);
      setInventario(inv.items); setOrdenes(ord.items); setError(null);
    } catch (e) {
      if (e instanceof ApiError && e.code === "UNAUTHENTICATED") {
        setError("Tu sesión expiró. Vuelve a iniciar sesión.");
      } else {
        setError(e instanceof Error ? e.message : "Error al cargar los datos.");
      }
    } finally { setCargando(false); }
  }, []);

  useEffect(() => { void recargar(); }, [recargar]);

  /** EP-15: el ajuste persiste y deja registro de auditoría (REQ-06). */
  const ajustar = async (v: InventoryResponse) => {
    const valor = window.prompt(
      `Nuevas existencias para ${v.productName} · talla ${v.size}:`, String(v.availableUnits));
    if (valor === null) return;
    const n = Number(valor);
    if (!Number.isInteger(n) || n < 0) {
      window.alert("Ingresa un número entero igual o mayor que cero."); return;
    }
    try { await ajustarInventario(v.variantId, n, "Ajuste manual desde el panel"); await recargar(); }
    catch (e) { window.alert(e instanceof Error ? e.message : "No se pudo ajustar"); }
  };

  const bajos = inventario.filter(v => v.availableUnits > 0 && v.availableUnits <= 5).length;
  const agotados = inventario.filter(v => v.availableUnits === 0).length;
  const ventas = ordenes.filter(o => o.status !== "CANCELADA").reduce((s, o) => s + o.totalCop, 0);

  return (
    <div className="admin-shell">
      <aside className="admin-side">
        <button className="logo" onClick={exit}>Tienda<span>Local</span></button>
        <span className="admin-chip">Modo administrador</span>
        <nav>{[["Inventario", "grid"], ["Pedidos", "bag"], ["Estadísticas", "chart"]].map(([x, icon]) => (
          <button className={tab === x ? "active" : ""} onClick={() => setTab(x)} key={x}><Icon name={icon}/>{x}</button>
        ))}</nav>
        <button className="exit" onClick={exit}>Cerrar sesión</button>
      </aside>
      <main className="admin-main">
        <header>
          <div><span className="eyebrow">Panel del negocio</span><h1>{tab}</h1>
            <p>Datos en vivo desde la API.</p></div>
          <button className="admin-avatar" onClick={() => void recargar()} title="Actualizar">EO</button>
        </header>

        {error && <div className="stock-warning" role="alert">{error}</div>}
        {cargando && <div className="admin-placeholder"><h2>Cargando…</h2></div>}

        {!cargando && tab === "Inventario" && <>
          <div className="admin-metrics">
            <article><span>Variantes activas</span><strong>{inventario.length}</strong><small>Inventario completo</small></article>
            <article><span>Poco inventario</span><strong>{bajos}</strong><small>5 unidades o menos</small></article>
            <article><span>Agotadas</span><strong>{agotados}</strong><small>Sin existencias</small></article>
          </div>
          <div className="inventory-head">
            <div><h2>Inventario por variante</h2><p>Haz clic en una fila para ajustar sus existencias.</p></div>
          </div>
          <div className="inventory">
            {inventario.map(v => (
              <article key={v.variantId}>
                <Foto src={v.imageUrl} alt={v.productName} loading="lazy"/>
                <div><strong>{v.productName}</strong><span>{v.categoryName ?? v.sku} · talla {v.size}</span></div>
                <b>{v.priceCop ? cop(v.priceCop) : "—"}</b>
                <span className={v.availableUnits <= 5 ? "low" : ""}>{v.availableUnits} unidades</span>
                <div>
                  <button onClick={() => void ajustar(v)} title={`Ajustar ${v.productName} talla ${v.size}`}>
                    Ajustar
                  </button>
                </div>
              </article>
            ))}
          </div>
        </>}

        {!cargando && tab === "Pedidos" && (
          ordenes.length ? (
            <div className="inventory">
              {ordenes.map(o => (
                <article key={o.id}>
                  <div><strong>#{o.orderNumber}</strong><span>{o.customerName ?? ""}</span></div>
                  <b>{cop(o.totalCop)}</b>
                  <span>{o.itemCount ?? "—"} líneas</span>
                  <span>{o.status}</span>
                  <span>{fechaLocal(o.createdAt)}</span>
                </article>
              ))}
            </div>
          ) : <div className="admin-placeholder"><Icon name="bag"/><h2>Aún no hay pedidos</h2>
                <p>Los pedidos confirmados en la tienda aparecerán aquí.</p></div>
        )}

        {!cargando && tab === "Estadísticas" && (
          <div className="admin-metrics large">
            <article><span>Ventas registradas</span><strong>{cop(ventas)}</strong><small>Órdenes no canceladas</small></article>
            <article><span>Pedidos</span><strong>{ordenes.length}</strong>
              <small>Ticket promedio {ordenes.length ? cop(Math.round(ventas / ordenes.length)) : "$0"}</small></article>
          </div>
        )}
      </main>
    </div>
  );
}

function Footer({ go }: { go: (v: View) => void }) {
  return (
    <footer>
      <div className="footer-main">
        <div>
          <button className="logo" onClick={() => go("home")}>Tienda<span>Local</span></button>
          <p>Diseño independiente y artesanía contemporánea, directo de manos bogotanas.</p>
          <span>Bogotá, Colombia</span>
        </div>
        {[["Ayuda", "Envíos y entregas", "Cambios", "Contáctanos"],
          ["Sobre TiendaLocal", "Nuestra historia", "Artesanos", "Vende con nosotros"],
          ["Legal", "Privacidad", "Términos", "Tratamiento de datos"]].map(group => (
          <div key={group[0]}>
            <strong>{group[0]}</strong>
            {group.slice(1).map(x => (
              <button key={x} onClick={() => group[0] === "Sobre TiendaLocal" && x === "Vende con nosotros"
                ? go("login")
                : window.alert(`${x}: esta información estará disponible próximamente.`)}>{x}</button>
            ))}
          </div>
        ))}
      </div>
      <div className="footer-bottom">
        <span>© 2026 TiendaLocal</span>
        <span>Aviso: checkout simulado con fines académicos</span>
      </div>
    </footer>
  );
}

export default function App() {
  const [view, setView] = useState<View>("home");
  const [productos, setProductos] = useState<ProductSummaryResponse[]>([]);
  const [categorias, setCategorias] = useState<CategoryResponse[]>([]);
  const [cargando, setCargando] = useState(true);
  const [fallo, setFallo] = useState<string | null>(null);
  const [saved, setSaved] = useState<string[]>([]);
  const [carrito, setCarrito] = useState<ItemCarrito[]>([]);
  const [pedidos, setPedidos] = useState<OrderResponse[]>([]);
  const [ultimaOrden, setUltimaOrden] = useState<OrderResponse | null>(null);
  const [detalle, setDetalle] = useState<ProductResponse | null>(null);
  const [cargandoDetalle, setCargandoDetalle] = useState(false);
  const [searching, setSearching] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

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

  const go = (next: View) => {
    if (next !== "checkout") setUltimaOrden(null);
    setView(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const goSection = (id: string) => {
    setView("home");
    window.setTimeout(() => document.getElementById(id)?.scrollIntoView({ behavior: "smooth" }), 0);
  };

  /** El resumen del catálogo no trae los identificadores de variante:
      el detalle se pide por slug, que es la ruta pública (EP-03). */
  const abrir = useCallback(async (p: ProductSummaryResponse) => {
    setDetalle(null); setCargandoDetalle(true); go("product");
    try { setDetalle(await obtenerProducto(p.slug)); }
    catch (e) {
      setAviso(e instanceof Error ? e.message : "No se pudo abrir el producto");
      go("home");
    } finally { setCargandoDetalle(false); }
  }, []);

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
      variantes con identificador. Si hay una sola disponible, la agrega. */
  const agregarRapido = async (p: ProductSummaryResponse) => {
    if (!p.inStock) { setAviso(`${p.name} no tiene existencias`); return; }
    try {
      const completo = await obtenerProducto(p.slug);
      const disponibles = completo.variants.filter(v => v.inStock);
      if (disponibles.length === 1) { agregarVariante(completo, disponibles[0]); return; }
      setDetalle(completo); go("product");
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
    setPedidos(p => [orden, ...p]);
    setUltimaOrden(orden);
    setCarrito([]);
    // Refresco silencioso: recarga existencias sin desmontar la vista,
    // que es lo que borraría la confirmación que el comprador debe ver.
    void cargar(true);
    return orden;
  };

  const entrarAdmin = async (email: string, clave: string) => {
    await iniciarSesion(email, clave);
    go("admin");
  };

  const salirAdmin = () => { cerrarSesion(); go("home"); };

  const unidades = carrito.reduce((s, i) => s + i.quantity, 0);

  if (view === "login") {
    return <Login close={() => go("home")} entrarAdmin={entrarAdmin} irPerfil={() => go("profile")}/>;
  }
  if (view === "admin") return <Admin exit={salirAdmin}/>;

  if (cargando) {
    return <div className="page empty" style={{ minHeight: "60vh" }}>
      <h2>Cargando catálogo…</h2><p>Consultando el inventario disponible.</p></div>;
  }

  if (fallo) {
    return <div className="page empty" style={{ minHeight: "60vh" }}>
      <h2>No pudimos cargar el catálogo</h2>
      <p>{fallo}</p>
      <button className="primary" onClick={() => void cargar()}>Reintentar</button>
    </div>;
  }

  const relacionados = detalle
    ? productos.filter(p => p.categoryName === detalle.category.name && p.id !== detalle.id).slice(0, 3)
    : [];

  return (
    <>
      <Header go={go} goSection={goSection} search={() => setSearching(true)}
              favCount={saved.length} cartCount={unidades}/>
      {view === "home" && <Home productos={productos} categorias={categorias} saved={saved}
        toggle={toggle} add={agregarRapido} abrir={abrir} go={go}/>}
      {view === "product" && <ProductDetail producto={detalle} cargando={cargandoDetalle}
        relacionados={relacionados} saved={detalle ? saved.includes(detalle.id) : false}
        toggle={() => detalle && toggle(detalle.id)}
        agregar={agregarVariante} abrir={abrir} go={go}/>}
      {view === "favorites" && <Favorites productos={productos} ids={saved} toggle={toggle}
        add={agregarRapido} abrir={abrir} go={go}/>}
      {view === "cart" && <Cart items={carrito} cambiar={cambiarCantidad} quitar={quitar} go={go}/>}
      {view === "checkout" && <Checkout items={carrito} orden={ultimaOrden}
        confirmar={confirmarPedido} go={go}/>}
      {view === "profile" && <Profile pedidos={pedidos} go={go}/>}
      {searching && <SearchModal productos={productos} close={() => setSearching(false)} abrir={abrir}/>}
      {aviso && <div className="toast" role="status">{aviso}</div>}
    </>
  );
}
