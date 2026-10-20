/* =====================================================================
 * Alta y edición de productos en el panel (EP-12, EP-14, EP-16, EP-22,
 * EP-25).
 *
 * /admin/productos/nuevo crea el producto con sus tallas y existencias en
 * un solo envío (REQ-06.4) y lleva a su edición. /admin/productos/<id>
 * edita los datos, agrega tallas y carga fotografías.
 *
 * Lo que la pantalla no ofrece, a propósito y por contrato: borrar
 * productos (RN-23) y quitar o reemplazar tallas desde el formulario de
 * datos; reemplazar la lista borraría por accidente tallas con ventas.
 * ===================================================================== */

import { useId, useState, type FormEvent, type ReactNode } from "react";
import {
  IMAGEN_MAX_BYTES, IMAGEN_TIPOS, TALLAS, agregarVariante, cargarImagen, cop, crearProducto,
  editarProducto, fechaHoraLocal, listarCategorias, obtenerProductoAdmin,
  type ProductResponse, type ProductUpdateRequest,
} from "./api";
import { Estado, mensajeDe, useCarga } from "./adminComun";
import { Icon } from "./componentes";
import { Enlace, useNavegacion } from "./navegacion";
import { rutas } from "./rutas";

/** Aviso que la pantalla de alta deja para la de edición: el «se creó» debe
 *  verse donde la administradora aterriza, no en la página que se fue. */
let avisoPendiente: string | null = null;

/** Etiqueta asociada por `id` al control que se dibuja dentro. */
function Campo({ etiqueta, ayuda, children }: {
  etiqueta: string; ayuda?: string; children: (id: string, ayudaId?: string) => ReactNode;
}) {
  const id = useId();
  const ayudaId = ayuda ? `${id}-ayuda` : undefined;
  return (
    <div className="field">
      <label htmlFor={id}>{etiqueta}</label>
      {children(id, ayudaId)}
      {ayuda && <small id={ayudaId} className="campo-ayuda">{ayuda}</small>}
    </div>
  );
}

function SugerenciasTallas({ id }: { id: string }) {
  return <datalist id={id}>{TALLAS.map(t => <option key={t} value={t}/>)}</datalist>;
}

/* ------------------------------------------------------------------ alta */

type FilaTalla = { clave: number; size: string; sku: string; initialStock: string };

export function NuevoProducto() {
  const { ir } = useNavegacion();
  const categorias = useCarga(listarCategorias, []);
  const [tallas, setTallas] = useState<FilaTalla[]>([{ clave: 1, size: "", sku: "", initialStock: "0" }]);
  const [fallo, setFallo] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const listaTallas = useId();

  if (!categorias.datos) return <Estado cargando={categorias.cargando} error={categorias.error}/>;

  const cambiar = (clave: number, campo: keyof FilaTalla, valor: string) =>
    setTallas(ts => ts.map(t => t.clave === clave ? { ...t, [campo]: valor } : t));

  const enviar = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setFallo(null); setEnviando(true);
    try {
      const p = await crearProducto({
        name: String(f.get("name")),
        description: String(f.get("description") ?? "") || null,
        priceCop: Number(f.get("priceCop")),
        categoryId: String(f.get("categoryId")),
        published: f.get("published") === "on",
        variants: tallas.map(t => ({
          size: t.size.trim(),
          initialStock: Number(t.initialStock),
          ...(t.sku.trim() ? { sku: t.sku.trim() } : {}),
        })),
      });
      avisoPendiente = `«${p.name}» se creó ${p.published ? "y ya está a la vista en la tienda" : "sin publicar"}. Ahora puedes cargar sus fotografías.`;
      ir(rutas.admin("productos", { id: p.id }));
    } catch (err) { setFallo(mensajeDe(err)); } finally { setEnviando(false); }
  };

  return <>
    <Enlace a={rutas.admin("productos")} className="breadcrumb">← Productos</Enlace>
    <form className="admin-formulario" onSubmit={e => void enviar(e)}>
      <section className="admin-tarjeta">
        <h2>Datos del producto</h2>
        <Campo etiqueta="Nombre">{id => <input id={id} name="name" required minLength={3} maxLength={120} autoFocus/>}</Campo>
        <Campo etiqueta="Descripción" ayuda="Opcional. Hasta 2000 caracteres.">
          {(id, ayuda) => <textarea id={id} name="description" maxLength={2000} rows={4} aria-describedby={ayuda}/>}
        </Campo>
        <div className="form-row">
          <Campo etiqueta="Precio (COP)" ayuda="Con IVA incluido, sin puntos.">
            {(id, ayuda) => <input id={id} name="priceCop" type="number" min={1} step={1} required aria-describedby={ayuda}/>}
          </Campo>
          <Campo etiqueta="Categoría">
            {id => <select id={id} name="categoryId" required defaultValue="">
              <option value="" disabled>Elige una categoría</option>
              {categorias.datos!.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>}
          </Campo>
        </div>
      </section>

      <fieldset className="admin-tarjeta">
        <legend><h2>Tallas y existencias iniciales</h2></legend>
        <p className="admin-nota">Cada talla es una unidad vendible (RN-05). Si dejas el SKU vacío, se genera con el
          formato de la tienda. Las existencias iniciales quedan en la auditoría.</p>
        <SugerenciasTallas id={listaTallas}/>
        {tallas.map((t, i) => (
          <div className="admin-fila-talla" key={t.clave} role="group" aria-label={`Talla ${i + 1}`}>
            <Campo etiqueta="Talla">{id => <input id={id} value={t.size} required maxLength={20} list={listaTallas}
              onChange={e => cambiar(t.clave, "size", e.target.value)}/>}</Campo>
            <Campo etiqueta="SKU (opcional)">{id => <input id={id} value={t.sku} maxLength={40} pattern="[A-Za-z0-9-]+"
              title="Letras sin tilde, dígitos y guiones" onChange={e => cambiar(t.clave, "sku", e.target.value)}/>}</Campo>
            <Campo etiqueta="Existencias">{id => <input id={id} type="number" min={0} step={1} required value={t.initialStock}
              onChange={e => cambiar(t.clave, "initialStock", e.target.value)}/>}</Campo>
            <button type="button" className="secondary" disabled={tallas.length === 1}
                    onClick={() => setTallas(ts => ts.filter(x => x.clave !== t.clave))}
                    aria-label={`Quitar la talla ${i + 1}`}><Icon name="trash"/></button>
          </div>
        ))}
        <button type="button" className="secondary" disabled={tallas.length >= 20}
                onClick={() => setTallas(ts => [...ts, { clave: Math.max(...ts.map(x => x.clave)) + 1, size: "", sku: "", initialStock: "0" }])}>
          <Icon name="plus"/> Agregar otra talla</button>
      </fieldset>

      <section className="admin-tarjeta">
        <label className="check"><input type="checkbox" name="published"/>
          <span>Publicar de inmediato. Si no, queda oculto hasta que lo publiques; así puedes cargar las fotos antes.</span></label>
        {fallo && <p className="stock-warning" role="alert">{fallo}</p>}
        <div className="admin-acciones">
          <button className="admin-primary" type="submit" disabled={enviando}>{enviando ? "Creando…" : "Crear producto"}</button>
          <Enlace a={rutas.admin("productos")} className="secondary">Cancelar</Enlace>
        </div>
      </section>
    </form>
  </>;
}

/* --------------------------------------------------------------- edición */

export function EditarProducto({ id, vuelta }: { id: string; vuelta: number }) {
  const [recarga, setRecarga] = useState(0);
  const { datos: p, setDatos, error, cargando } = useCarga(() => obtenerProductoAdmin(id), [id, vuelta, recarga]);
  const categorias = useCarga(listarCategorias, []);
  const [aviso, setAviso] = useState<string | null>(() => { const a = avisoPendiente; avisoPendiente = null; return a; });

  if (!p) return <><Enlace a={rutas.admin("productos")} className="breadcrumb">← Productos</Enlace>
    <Estado cargando={cargando} error={error}/></>;

  const recargar = (mensaje: string) => { setAviso(mensaje); setRecarga(r => r + 1); };

  return <>
    <Enlace a={rutas.admin("productos")} className="breadcrumb">← Productos</Enlace>
    <div className="admin-detalle-titulo admin-producto-titulo">
      <h2>{p.name}</h2>
      <span className={`estado ${p.published ? "estado-entregada" : "estado-cancelada"}`}>{p.published ? "Publicado" : "Oculto"}</span>
      {p.published && <Enlace a={rutas.producto(p.slug)}>Ver en la tienda <Icon name="arrow"/></Enlace>}
    </div>
    <p className="admin-nota">
      Dirección pública: <code>/producto/{p.slug}</code> (no cambia aunque edites el nombre, para no romper enlaces ya compartidos)
      {p.updatedAt && <> · Última modificación: {fechaHoraLocal(p.updatedAt)}</>}
    </p>
    <p className="admin-vivo" role="status" aria-live="polite">{aviso}</p>

    <div className="admin-producto">
      <DatosProducto producto={p} categorias={categorias.datos ?? []}
        alGuardar={(nuevo, mensaje) => { setDatos(nuevo); setAviso(mensaje); }}/>
      <div className="admin-producto-lateral">
        <Tallas producto={p} alAgregar={recargar}/>
        <Fotografias producto={p} alCargar={recargar}/>
      </div>
    </div>
  </>;
}

function DatosProducto({ producto: p, categorias, alGuardar }: {
  producto: ProductResponse; categorias: { id: string; name: string }[];
  alGuardar: (p: ProductResponse, mensaje: string) => void;
}) {
  const [fallo, setFallo] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  /** EP-22 aplica solo lo enviado: se manda únicamente lo que cambió. */
  const enviar = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const nuevo = {
      name: String(f.get("name")).trim(),
      description: String(f.get("description")).trim() || null,
      priceCop: Number(f.get("priceCop")),
      categoryId: String(f.get("categoryId")),
      published: f.get("published") === "on",
    };
    const cambios: ProductUpdateRequest = {};
    if (nuevo.name !== p.name) cambios.name = nuevo.name;
    if (nuevo.description !== (p.description ?? null)) cambios.description = nuevo.description;
    if (nuevo.priceCop !== p.priceCop) cambios.priceCop = nuevo.priceCop;
    if (nuevo.categoryId !== p.category.id) cambios.categoryId = nuevo.categoryId;
    if (nuevo.published !== p.published) cambios.published = nuevo.published;
    if (!Object.keys(cambios).length) { alGuardar(p, "No había cambios que guardar."); return; }

    setFallo(null); setEnviando(true);
    try {
      const guardado = await editarProducto(p.id, cambios);
      alGuardar(guardado, "Cambios guardados." + ("priceCop" in cambios
        ? " El precio nuevo rige para las próximas compras; los pedidos anteriores conservan el suyo." : ""));
    } catch (err) { setFallo(mensajeDe(err)); } finally { setEnviando(false); }
  };

  return (
    // `key` con la fecha de modificación: tras guardar, el formulario se
    // vuelve a montar con los valores que confirmó el servidor.
    <form key={p.updatedAt ?? ""} className="admin-tarjeta" onSubmit={e => void enviar(e)}>
      <h2>Datos</h2>
      <Campo etiqueta="Nombre">{id => <input id={id} name="name" required minLength={3} maxLength={120} defaultValue={p.name}/>}</Campo>
      <Campo etiqueta="Descripción">{id => <textarea id={id} name="description" maxLength={2000} rows={5} defaultValue={p.description ?? ""}/>}</Campo>
      <div className="form-row">
        <Campo etiqueta="Precio (COP)" ayuda={`Actual: ${cop(p.priceCop)}`}>
          {(id, ayuda) => <input id={id} name="priceCop" type="number" min={1} step={1} required defaultValue={p.priceCop} aria-describedby={ayuda}/>}
        </Campo>
        <Campo etiqueta="Categoría">
          {id => <select id={id} name="categoryId" required defaultValue={p.category.id}>
            {(categorias.length ? categorias : [p.category]).map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>}
        </Campo>
      </div>
      <label className="check"><input type="checkbox" name="published" defaultChecked={p.published}/>
        <span>Publicado: visible en la tienda. Exige al menos una talla activa (RN-21).</span></label>
      {fallo && <p className="stock-warning" role="alert">{fallo}</p>}
      <div className="admin-acciones">
        <button className="admin-primary" type="submit" disabled={enviando}>{enviando ? "Guardando…" : "Guardar cambios"}</button>
      </div>
    </form>
  );
}

function Tallas({ producto: p, alAgregar }: { producto: ProductResponse; alAgregar: (mensaje: string) => void }) {
  const [fallo, setFallo] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const listaTallas = useId();

  /** EP-14. Las existencias iniciales quedan en la auditoría (RN-24). */
  const enviar = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formulario = e.currentTarget;
    const f = new FormData(formulario);
    setFallo(null); setEnviando(true);
    try {
      const sku = String(f.get("sku")).trim();
      const v = await agregarVariante(p.id, {
        size: String(f.get("size")).trim(),
        initialStock: Number(f.get("initialStock")),
        ...(sku ? { sku } : {}),
      });
      formulario.reset();
      alAgregar(`Talla ${v.size} agregada (SKU ${v.sku}) con ${v.availableUnits} unidades.`);
    } catch (err) { setFallo(mensajeDe(err)); } finally { setEnviando(false); }
  };

  return (
    <section className="admin-tarjeta">
      <h2>Tallas</h2>
      {p.variants.length ? (
        <div className="admin-desborde">
          <table className="admin-tabla">
            <caption className="sr-only">Tallas de {p.name}</caption>
            <thead><tr><th scope="col">Talla</th><th scope="col">SKU</th><th scope="col">Existencias</th></tr></thead>
            <tbody>{p.variants.map(v => (
              <tr key={v.id}><td>{v.size}</td><td><code>{v.sku}</code></td>
                <td className={v.availableUnits <= 5 ? "low" : ""}>{v.availableUnits}</td></tr>
            ))}</tbody>
          </table>
        </div>
      ) : <p className="admin-nota">Sin tallas activas: no se puede publicar ni comprar.</p>}
      <p className="admin-nota">Para corregir existencias usa <Enlace a={rutas.admin("inventario")}>Inventario</Enlace>: allí cada ajuste pide motivo.</p>
      <form className="admin-fila-talla" onSubmit={e => void enviar(e)} aria-label="Agregar talla">
        <SugerenciasTallas id={listaTallas}/>
        <Campo etiqueta="Talla nueva">{id => <input id={id} name="size" required maxLength={20} list={listaTallas}/>}</Campo>
        <Campo etiqueta="SKU (opcional)">{id => <input id={id} name="sku" maxLength={40} pattern="[A-Za-z0-9-]+"
          title="Letras sin tilde, dígitos y guiones"/>}</Campo>
        <Campo etiqueta="Existencias">{id => <input id={id} name="initialStock" type="number" min={0} step={1} required defaultValue={0}/>}</Campo>
        <button className="admin-primary" type="submit" disabled={enviando}><Icon name="plus"/> Agregar</button>
        {fallo && <p className="stock-warning" role="alert">{fallo}</p>}
      </form>
    </section>
  );
}

function Fotografias({ producto: p, alCargar }: { producto: ProductResponse; alCargar: (mensaje: string) => void }) {
  const [fallo, setFallo] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  /** EP-16. Se avisa antes de subir lo que de antemano se sabe que el
   *  servidor rechazará; él vuelve a comprobarlo por el contenido. */
  const enviar = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formulario = e.currentTarget;
    const f = new FormData(formulario);
    const archivo = f.get("file");
    if (!(archivo instanceof File) || !archivo.size) { setFallo("Elige un archivo."); return; }
    if (!IMAGEN_TIPOS.includes(archivo.type)) { setFallo("Solo se admiten imágenes JPEG, PNG o WebP."); return; }
    if (archivo.size > IMAGEN_MAX_BYTES) {
      setFallo(`La imagen pesa ${(archivo.size / 1024 / 1024).toFixed(1)} MB; el máximo es 5 MB.`); return;
    }
    setFallo(null); setEnviando(true);
    try {
      const img = await cargarImagen(p.id, archivo, String(f.get("alt")).trim());
      formulario.reset();
      alCargar(`Fotografía cargada y optimizada (${img.width}×${img.height}, WebP).`);
    } catch (err) { setFallo(mensajeDe(err)); } finally { setEnviando(false); }
  };

  return (
    <section className="admin-tarjeta">
      <h2>Fotografías</h2>
      {p.images.length ? (
        <ul className="admin-galeria">
          {p.images.map((img, i) => (
            <li key={img.id}>
              <img src={img.url} alt={img.alt ?? ""} width={img.width ?? undefined} height={img.height ?? undefined} loading="lazy"/>
              <span>{i === 0 ? "Principal · " : ""}{img.alt}</span>
            </li>
          ))}
        </ul>
      ) : <p className="admin-nota">Aún no tiene fotografías: en la tienda se verá un bloque de color.</p>}
      <form onSubmit={e => void enviar(e)} aria-label="Cargar fotografía">
        <Campo etiqueta="Archivo" ayuda="JPEG, PNG o WebP de hasta 5 MB. Se reduce a 1200 px y se convierte a WebP; se quitan los datos de ubicación de la cámara.">
          {(id, ayuda) => <input id={id} name="file" type="file" required accept={IMAGEN_TIPOS.join(",")} aria-describedby={ayuda}/>}
        </Campo>
        <Campo etiqueta="Texto alternativo" ayuda="Describe lo que se ve, para quien usa lector de pantalla (obligatorio, RNF-03).">
          {(id, ayuda) => <input id={id} name="alt" required maxLength={160} aria-describedby={ayuda}
            placeholder="Ej.: Gorra negra bordada vista de frente"/>}
        </Campo>
        {fallo && <p className="stock-warning" role="alert">{fallo}</p>}
        <div className="admin-acciones">
          <button className="admin-primary" type="submit" disabled={enviando}>{enviando ? "Cargando…" : "Cargar fotografía"}</button>
        </div>
      </form>
    </section>
  );
}
