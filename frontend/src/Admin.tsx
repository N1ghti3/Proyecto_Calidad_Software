/* =====================================================================
 * Panel del negocio.
 *
 * Cada sección tiene su ruta (`/admin/inventario`, `/admin/pedidos/<id>`,
 * …) y carga sus propios datos. Antes el panel era una sola vista con
 * pestañas internas que solo mostraba inventario y pedidos: el backend ya
 * permitía cambiar estados, publicar productos y consultar la auditoría,
 * pero la interfaz no ofrecía ninguna de esas operaciones.
 *
 * Los ajustes se hacen con formularios en línea y no con `window.prompt`:
 * el cuadro del navegador bloquea la página, no se puede etiquetar, no deja
 * pedir el motivo que exige la auditoría (RN-25) y los lectores de pantalla
 * lo anuncian mal (RNF-03).
 * ===================================================================== */

import { useMemo, useState, type FormEvent } from "react";
import {
  TRANSICIONES, ajustarInventario, cambiarEstadoOrden, cop, fechaHoraLocal, fechaLocal,
  listarProductosAdmin, obtenerAuditoria, obtenerInventario, obtenerNotificaciones,
  obtenerOrdenAdmin, obtenerOrdenesAdmin, obtenerTodasLasOrdenes, publicarProducto, usuarioActual,
  type AdminProductSummaryResponse, type EstadoOrden, type InventoryResponse, type Page,
} from "./api";
import { Estado, mensajeDe, useCarga } from "./adminComun";
import { EditarProducto, NuevoProducto } from "./AdminProductos";
import { Foto, Icon } from "./componentes";
import { Enlace } from "./navegacion";
import { ETIQUETAS_ADMIN, SECCIONES_ADMIN, rutas, tituloAdmin, type SeccionAdmin } from "./rutas";

type RutaAdmin = { seccion: SeccionAdmin; id: string | null; pagina: number };

const ICONOS: Record<SeccionAdmin, string> = {
  inventario: "grid", pedidos: "bag", productos: "tag",
  auditoria: "list", notificaciones: "bell", estadisticas: "chart",
};

const ETIQUETA_ESTADO: Record<EstadoOrden, string> = {
  CONFIRMADA: "Confirmada", PREPARADA: "Preparada", ENTREGADA: "Entregada", CANCELADA: "Cancelada",
};

function Paginacion({ seccion, meta }: { seccion: SeccionAdmin; meta: Page<unknown>["meta"] }) {
  if (meta.totalPages <= 1) return null;
  return (
    <nav className="admin-paginacion" aria-label="Paginación">
      {meta.page > 1
        ? <Enlace a={rutas.admin(seccion, { pagina: meta.page - 1 })}>← Anterior</Enlace>
        : <span aria-hidden="true" />}
      <span>Página {meta.page} de {meta.totalPages} · {meta.totalItems} registros</span>
      {meta.page < meta.totalPages
        ? <Enlace a={rutas.admin(seccion, { pagina: meta.page + 1 })}>Siguiente →</Enlace>
        : <span aria-hidden="true" />}
    </nav>
  );
}

/* ------------------------------------------------------------ inventario */

function Inventario({ vuelta }: { vuelta: number }) {
  const { datos, setDatos, error, cargando } = useCarga(obtenerInventario, [vuelta]);
  const [editando, setEditando] = useState<string | null>(null);
  const [filtro, setFiltro] = useState("");
  const [aviso, setAviso] = useState<string | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);

  const filas = useMemo(() => {
    const q = filtro.trim().toLowerCase();
    return (datos ?? []).filter(v => !q || `${v.productName} ${v.sku} ${v.size}`.toLowerCase().includes(q));
  }, [datos, filtro]);

  if (!datos) return <Estado cargando={cargando} error={error}/>;

  const bajos = datos.filter(v => v.stockQuantity > 0 && v.stockQuantity <= 5).length;
  const agotados = datos.filter(v => v.stockQuantity === 0).length;

  /** EP-15: fija el valor final; el ajuste y su auditoría van en la misma transacción. */
  const guardar = async (v: InventoryResponse, e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setFallo(null);
    try {
      const nueva = await ajustarInventario(v.variantId, Number(f.get("stock")), String(f.get("motivo")).trim());
      setDatos(ds => ds && ds.map(x => x.variantId === v.variantId ? { ...x, ...nueva } : x));
      setEditando(null);
      setAviso(`${v.productName} · talla ${v.size}: ${nueva.stockQuantity} unidades. El cambio quedó en la auditoría.`);
    } catch (err) { setFallo(mensajeDe(err)); }
  };

  return <>
    <div className="admin-metrics">
      <article><span>Variantes activas</span><strong>{datos.length}</strong><small>Inventario completo</small></article>
      <article><span>Poco inventario</span><strong>{bajos}</strong><small>5 unidades o menos</small></article>
      <article><span>Agotadas</span><strong>{agotados}</strong><small>Sin existencias</small></article>
    </div>
    <div className="inventory-head">
      <div><h2>Inventario por variante</h2><p>Ordenado de menos a más existencias.</p></div>
      <label className="field admin-filtro"><span>Buscar</span>
        <input type="search" value={filtro} onChange={e => setFiltro(e.target.value)} placeholder="Producto, SKU o talla"/>
      </label>
    </div>
    <p className="admin-vivo" role="status" aria-live="polite">{aviso}</p>
    <div className="inventory">
      {filas.map(v => (
        <article key={v.variantId} className={editando === v.variantId ? "editando" : ""}>
          <Foto src={v.imageUrl} alt="" loading="lazy"/>
          <div><strong>{v.productName}</strong><span>{v.categoryName ?? v.sku} · talla {v.size} · {v.sku}</span></div>
          <b>{v.priceCop ? cop(v.priceCop) : "—"}</b>
          <span className={v.stockQuantity <= 5 ? "low" : ""}>{v.stockQuantity} {v.stockQuantity === 1 ? "unidad" : "unidades"}</span>
          <div>
            <button type="button" aria-expanded={editando === v.variantId}
                    onClick={() => { setEditando(editando === v.variantId ? null : v.variantId); setFallo(null); }}>
              Ajustar<span className="sr-only"> {v.productName} talla {v.size}</span>
            </button>
          </div>
          {editando === v.variantId && (
            <form className="admin-ajuste" onSubmit={e => void guardar(v, e)}>
              <label className="field"><span>Existencias finales</span>
                <input name="stock" type="number" min={0} step={1} required defaultValue={v.stockQuantity} autoFocus/>
              </label>
              <label className="field"><span>Motivo (queda en la auditoría)</span>
                <input name="motivo" required minLength={3} maxLength={120} defaultValue="Conteo físico"/>
              </label>
              <div className="admin-acciones">
                <button className="admin-primary" type="submit">Guardar</button>
                <button className="secondary" type="button" onClick={() => setEditando(null)}>Cancelar</button>
              </div>
              {fallo && <p className="stock-warning" role="alert">{fallo}</p>}
            </form>
          )}
        </article>
      ))}
      {!filas.length && <p className="admin-vacio">Ninguna variante coincide con «{filtro}».</p>}
    </div>
  </>;
}

/* --------------------------------------------------------------- pedidos */

function Pedidos({ pagina, vuelta }: { pagina: number; vuelta: number }) {
  const { datos, error, cargando } = useCarga(() => obtenerOrdenesAdmin(pagina), [pagina, vuelta]);
  if (!datos) return <Estado cargando={cargando} error={error}/>;
  if (!datos.items.length) {
    return <div className="admin-placeholder"><Icon name="bag"/><h2>Aún no hay pedidos</h2>
      <p>Los pedidos confirmados en la tienda aparecerán aquí.</p></div>;
  }
  return <>
    <div className="inventory admin-lista">
      {datos.items.map(o => (
        <Enlace key={o.id} a={rutas.admin("pedidos", { id: o.id })} className="admin-fila">
          <div><strong>#{o.orderNumber}</strong><span>{o.customerName ?? ""}</span></div>
          <b>{cop(o.totalCop)}</b>
          <span>{o.itemCount ?? "—"} {o.itemCount === 1 ? "línea" : "líneas"}</span>
          <span className={`estado estado-${o.status.toLowerCase()}`}>{ETIQUETA_ESTADO[o.status]}</span>
          <span>{fechaLocal(o.createdAt)}</span>
        </Enlace>
      ))}
    </div>
    <Paginacion seccion="pedidos" meta={datos.meta}/>
  </>;
}

function DetallePedido({ id, vuelta }: { id: string; vuelta: number }) {
  const { datos: orden, setDatos, error, cargando } = useCarga(() => obtenerOrdenAdmin(id), [id, vuelta]);
  const [cancelando, setCancelando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  if (!orden) return <><Enlace a={rutas.admin("pedidos")} className="breadcrumb">← Pedidos</Enlace>
    <Estado cargando={cargando} error={error}/></>;

  /** EP-18. Cancelar devuelve las unidades al inventario en el servidor. */
  const cambiar = async (estado: EstadoOrden, motivo?: string) => {
    setFallo(null); setEnviando(true);
    try {
      const nueva = await cambiarEstadoOrden(orden.id, estado, motivo);
      setDatos(nueva); setCancelando(false);
      setAviso(`El pedido pasó al estado «${ETIQUETA_ESTADO[nueva.status]}».` +
        (estado === "CANCELADA" ? " Las unidades volvieron al inventario." : ""));
    } catch (e) { setFallo(mensajeDe(e)); } finally { setEnviando(false); }
  };
  const siguientes = TRANSICIONES[orden.status];

  return <>
    <Enlace a={rutas.admin("pedidos")} className="breadcrumb">← Pedidos</Enlace>
    <div className="admin-detalle">
      <section>
        <div className="admin-detalle-titulo">
          <h2>#{orden.orderNumber}</h2>
          <span className={`estado estado-${orden.status.toLowerCase()}`}>{ETIQUETA_ESTADO[orden.status]}</span>
        </div>
        {orden.createdAt && <p className="admin-nota">Registrado el {fechaHoraLocal(orden.createdAt)}</p>}
        <div className="admin-desborde">
        <table className="admin-tabla">
          <caption className="sr-only">Líneas del pedido</caption>
          <thead><tr><th scope="col">Producto</th><th scope="col">Talla</th><th scope="col">Cant.</th><th scope="col">Precio</th><th scope="col">Total</th></tr></thead>
          <tbody>
            {orden.items.map(l => (
              <tr key={l.variantId}><td>{l.productName}</td><td>{l.size}</td><td>{l.quantity}</td>
                <td>{cop(l.unitPriceCop)}</td><td>{cop(l.lineTotalCop)}</td></tr>
            ))}
          </tbody>
          <tfoot><tr><th scope="row" colSpan={4}>Total</th><td>{cop(orden.totalCop)}</td></tr></tfoot>
        </table>
        </div>
      </section>
      <aside>
        <h2>Entrega</h2>
        <dl className="admin-datos">
          <dt>Comprador</dt><dd>{orden.customer.name}</dd>
          <dt>Correo</dt><dd>{orden.customer.email}</dd>
          <dt>Teléfono</dt><dd>{orden.customer.phone}</dd>
          <dt>Dirección</dt><dd>{orden.customer.address}, {orden.customer.city}</dd>
        </dl>
        <h2>Estado</h2>
        <p className="admin-vivo" role="status" aria-live="polite">{aviso}</p>
        {siguientes.length === 0
          ? <p className="admin-nota">«{ETIQUETA_ESTADO[orden.status]}» es un estado final: el pedido ya no se puede reabrir (RN-13).</p>
          : <div className="admin-acciones">
              {siguientes.filter(s => s !== "CANCELADA").map(s => (
                <button key={s} className="admin-primary" disabled={enviando} onClick={() => void cambiar(s)}>
                  Pasar a «{ETIQUETA_ESTADO[s]}»
                </button>
              ))}
              {siguientes.includes("CANCELADA") && !cancelando &&
                <button className="secondary" disabled={enviando} onClick={() => setCancelando(true)}>Cancelar pedido</button>}
            </div>}
        {cancelando && (
          <form className="admin-ajuste" onSubmit={e => {
            e.preventDefault();
            void cambiar("CANCELADA", String(new FormData(e.currentTarget).get("motivo")).trim());
          }}>
            <label className="field"><span>Motivo de la cancelación</span>
              <input name="motivo" required minLength={3} maxLength={120} autoFocus/></label>
            <div className="admin-acciones">
              <button className="admin-primary peligro" type="submit" disabled={enviando}>Confirmar cancelación</button>
              <button className="secondary" type="button" onClick={() => setCancelando(false)}>Volver</button>
            </div>
          </form>
        )}
        {fallo && <p className="stock-warning" role="alert">{fallo}</p>}
      </aside>
    </div>
  </>;
}

/* ------------------------------------------------------------- productos */

function Productos({ vuelta }: { vuelta: number }) {
  const { datos, setDatos, error, cargando } = useCarga(listarProductosAdmin, [vuelta]);
  const [aviso, setAviso] = useState<string | null>(null);
  const [fallo, setFallo] = useState<string | null>(null);
  if (!datos) return <Estado cargando={cargando} error={error}/>;

  /** EP-13. Despublicar no borra (RN-23): el producto sigue en las órdenes previas. */
  const alternar = async (p: AdminProductSummaryResponse) => {
    setFallo(null);
    try {
      const nuevo = await publicarProducto(p.id, !p.published);
      setDatos(ds => ds && ds.map(x => x.id === p.id ? nuevo : x));
      setAviso(`${p.name} ${nuevo.published ? "ya aparece" : "dejó de aparecer"} en la tienda.`);
    } catch (e) { setFallo(`${p.name}: ${mensajeDe(e)}`); }
  };

  return <>
    <div className="inventory-head">
      <div><h2>{datos.length} productos</h2>
        <p>{datos.filter(p => p.published).length} publicados · {datos.filter(p => !p.published).length} ocultos</p></div>
      <Enlace a={rutas.admin("productos", { id: "nuevo" })} className="admin-primary"><Icon name="plus"/> Nuevo producto</Enlace>
    </div>
    <p className="admin-vivo" role="status" aria-live="polite">{aviso}</p>
    {fallo && <p className="stock-warning" role="alert">{fallo}</p>}
    <div className="inventory">
      {datos.map(p => (
        <article key={p.id}>
          <Foto src={p.imageUrl} alt="" loading="lazy"/>
          <div><strong><Enlace a={rutas.admin("productos", { id: p.id })}>{p.name}</Enlace></strong>
            <span>{p.categoryName} · {p.sizes.join(", ") || "sin tallas"}</span></div>
          <b>{cop(p.priceCop)}</b>
          <span className={`estado ${p.published ? "estado-entregada" : "estado-cancelada"}`}>
            {p.published ? "Publicado" : "Oculto"}
          </span>
          <div>
            <button type="button" onClick={() => void alternar(p)}>
              {p.published ? "Ocultar" : "Publicar"}<span className="sr-only"> {p.name}</span>
            </button>
          </div>
        </article>
      ))}
    </div>
  </>;
}

/* ------------------------------------------------------------- auditoría */

const ENTIDAD: Record<string, string> = { INVENTORY: "Inventario", ORDER: "Pedido", PRODUCT: "Producto" };
const ORIGEN: Record<string, string> = { AJUSTE_MANUAL: "Ajuste manual", ORDEN: "Compra", CANCELACION: "Cancelación" };

function Auditoria({ pagina, vuelta }: { pagina: number; vuelta: number }) {
  const { datos, error, cargando } = useCarga(() => obtenerAuditoria(pagina), [pagina, vuelta]);
  if (!datos) return <Estado cargando={cargando} error={error}/>;
  return <>
    <p className="admin-nota">Registro de solo lectura (RN-25): ni la interfaz ni el rol de la aplicación pueden modificarlo.</p>
    <div className="admin-tabla-marco">
      <table className="admin-tabla">
        <caption className="sr-only">Registro de auditoría, página {datos.meta.page}</caption>
        <thead><tr><th scope="col">Fecha</th><th scope="col">Entidad</th><th scope="col">Origen</th><th scope="col">Cambio</th><th scope="col">Por</th><th scope="col">Motivo</th></tr></thead>
        <tbody>
          {datos.items.map(a => (
            <tr key={a.id}>
              <td>{fechaHoraLocal(a.createdAt)}</td>
              <td>{ENTIDAD[a.entityType] ?? a.entityType}</td>
              <td>{ORIGEN[a.source] ?? a.source}</td>
              <td><code>{a.oldValue ?? "—"}</code> → <code>{a.newValue}</code></td>
              {/* Sin autor puede significar una compra o un administrador que
                  ya no existe; solo el origen distingue ambos casos. */}
              <td>{a.performedBy ?? (a.source === "ORDEN" ? "Compra en la tienda" : "—")}</td>
              <td>{a.reason ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    <Paginacion seccion="auditoria" meta={datos.meta}/>
  </>;
}

/* -------------------------------------------------------- notificaciones */

function Notificaciones({ pagina, vuelta }: { pagina: number; vuelta: number }) {
  const { datos, error, cargando } = useCarga(() => obtenerNotificaciones(pagina), [pagina, vuelta]);
  if (!datos) return <Estado cargando={cargando} error={error}/>;
  return <>
    <p className="admin-nota">El envío de correo aún no está configurado (DT-01): las notificaciones quedan
      pendientes y esta lista muestra a quién falta avisar (RN-15).</p>
    <div className="admin-tabla-marco">
      <table className="admin-tabla">
        <caption className="sr-only">Notificaciones, página {datos.meta.page}</caption>
        <thead><tr><th scope="col">Fecha</th><th scope="col">Para</th><th scope="col">Destinatario</th><th scope="col">Estado</th><th scope="col">Intentos</th><th scope="col">Pedido</th></tr></thead>
        <tbody>
          {datos.items.map(n => (
            <tr key={n.id}>
              <td>{fechaHoraLocal(n.createdAt)}</td>
              <td>{n.recipientType === "COMPRADOR" ? "Comprador" : "Administración"}</td>
              <td>{n.recipient}</td>
              <td>{n.status.charAt(0) + n.status.slice(1).toLowerCase()}</td>
              <td>{n.attempts}</td>
              <td><Enlace a={rutas.admin("pedidos", { id: n.orderId })}>Ver pedido</Enlace></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    <Paginacion seccion="notificaciones" meta={datos.meta}/>
  </>;
}

/* ---------------------------------------------------------- estadísticas */

function Estadisticas({ vuelta }: { vuelta: number }) {
  const { datos, error, cargando } = useCarga(obtenerTodasLasOrdenes, [vuelta]);
  if (!datos) return <Estado cargando={cargando} error={error}/>;
  const validas = datos.filter(o => o.status !== "CANCELADA");
  const ventas = validas.reduce((s, o) => s + o.totalCop, 0);
  const porEstado = (Object.keys(ETIQUETA_ESTADO) as EstadoOrden[])
    .map(e => [e, datos.filter(o => o.status === e).length] as const);
  return <>
    <div className="admin-metrics large">
      <article><span>Ventas registradas</span><strong>{cop(ventas)}</strong><small>Pedidos no cancelados</small></article>
      <article><span>Pedidos</span><strong>{validas.length}</strong>
        {/* Promedio sobre los pedidos válidos: incluir los cancelados en el
            divisor lo subestimaba. */}
        <small>Ticket promedio {validas.length ? cop(Math.round(ventas / validas.length)) : "$0"}</small></article>
    </div>
    <div className="admin-metrics">
      {porEstado.map(([e, n]) => (
        <article key={e}><span>{ETIQUETA_ESTADO[e]}</span><strong>{n}</strong>
          <small>{datos.length ? Math.round((n / datos.length) * 100) : 0}% del total</small></article>
      ))}
    </div>
  </>;
}

/* ----------------------------------------------------------------- marco */

export default function Admin({ ruta, salir }: { ruta: RutaAdmin; salir: () => void }) {
  // Cambiar este número vuelve a pedir los datos de la sección visible.
  const [vuelta, setVuelta] = useState(0);
  const usuario = usuarioActual();
  const iniciales = (usuario?.fullName ?? "Admin").split(/\s+/).map(p => p[0]).slice(0, 2).join("").toUpperCase();
  const titulo = tituloAdmin(ruta.seccion, ruta.id);

  return (
    <div className="admin-shell">
      <aside className="admin-side">
        <Enlace a={rutas.inicio} className="logo">Tienda<span>Local</span></Enlace>
        <span className="admin-chip">Modo administrador</span>
        <nav aria-label="Secciones del panel">
          {SECCIONES_ADMIN.map(s => (
            <Enlace key={s} a={rutas.admin(s)} activo="prefijo"><Icon name={ICONOS[s]}/>{ETIQUETAS_ADMIN[s]}</Enlace>
          ))}
        </nav>
        <button className="exit" onClick={salir}>Cerrar sesión</button>
      </aside>
      <main className="admin-main">
        <header>
          <div><span className="eyebrow">Panel del negocio</span><h1>{titulo}</h1>
            <p>{usuario ? `Sesión de ${usuario.fullName}` : "Datos en vivo desde la API."}</p></div>
          <div className="admin-cabecera-acciones">
            <button className="secondary" onClick={() => setVuelta(v => v + 1)}><Icon name="refresh"/> Actualizar</button>
            <span className="admin-avatar" aria-hidden="true">{iniciales}</span>
            <button className="secondary admin-salir-movil" onClick={salir}>Salir</button>
          </div>
        </header>

        {ruta.seccion === "inventario" && <Inventario vuelta={vuelta}/>}
        {ruta.seccion === "pedidos" && (ruta.id
          ? <DetallePedido id={ruta.id} vuelta={vuelta}/>
          : <Pedidos pagina={ruta.pagina} vuelta={vuelta}/>)}
        {ruta.seccion === "productos" && (
          ruta.id === "nuevo" ? <NuevoProducto/>
          : ruta.id ? <EditarProducto key={ruta.id} id={ruta.id} vuelta={vuelta}/>
          : <Productos vuelta={vuelta}/>)}
        {ruta.seccion === "auditoria" && <Auditoria pagina={ruta.pagina} vuelta={vuelta}/>}
        {ruta.seccion === "notificaciones" && <Notificaciones pagina={ruta.pagina} vuelta={vuelta}/>}
        {ruta.seccion === "estadisticas" && <Estadisticas vuelta={vuelta}/>}
      </main>
    </div>
  );
}
