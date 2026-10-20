/* Piezas visuales compartidas por la tienda y el panel. */

import { useEffect, useState, type ReactNode } from "react";

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
export function Foto({ src, alt, className, onClick, loading }: {
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
    // `loading="lazy"` por omisión: el catálogo trae más de una docena de
    // fotografías y pedirlas todas de golpe alarga la primera carga aunque
    // solo cuatro estén a la vista. `decoding="async"` evita además que la
    // decodificación de cada una bloquee el hilo que pinta la página.
    <img src={src} alt={alt} className={className} onClick={onClick}
         loading={loading ?? "lazy"} decoding="async"
         onError={() => setFalló(true)} />
  );
}

export function Icon({ name, filled = false }: { name: string; filled?: boolean }) {
  const paths: Record<string, ReactNode> = {
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
    tag: <><path d="M3 12V4h8l10 10-8 8L3 12Z"/><circle cx="7.5" cy="8.5" r="1.5"/></>,
    list: <><path d="M9 6h12M9 12h12M9 18h12"/><path d="M4 6h.01M4 12h.01M4 18h.01"/></>,
    bell: <><path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4l2-2Z"/><path d="M10 21h4"/></>,
  };
  return <svg aria-hidden="true" className="icon" viewBox="0 0 24 24" fill={filled ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}
