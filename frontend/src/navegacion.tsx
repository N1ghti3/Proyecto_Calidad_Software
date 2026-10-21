/* =====================================================================
 * Navegación entre rutas sin recargar la página.
 *
 * Los destinos se escriben como enlaces de verdad (`<a href>`), no como
 * botones con un manejador. Así funcionan las costumbres del navegador que
 * un botón no ofrece: abrir en otra pestaña con Ctrl/⌘ o la rueda, copiar
 * la dirección, ver el destino al pasar el puntero, y que un lector de
 * pantalla anuncie «enlace» en lugar de «botón» (RNF-03).
 *
 * El clic normal se intercepta y cambia la vista con `history.pushState`;
 * los clics con modificador se dejan pasar para que el navegador haga lo
 * suyo.
 * ===================================================================== */

import { createContext, useContext, type AnchorHTMLAttributes, type MouseEvent } from "react";

export type Ir = (destino: string, opciones?: { reemplazar?: boolean }) => void;

type Navegacion = { ubicacion: string; ir: Ir };

export const ContextoNavegacion = createContext<Navegacion>({
  ubicacion: "/",
  ir: () => { throw new Error("Falta <ContextoNavegacion.Provider>"); },
});

export const useNavegacion = () => useContext(ContextoNavegacion);

/** Lee la dirección actual del navegador: camino y consulta, sin el origen. */
export const direccionActual = () => window.location.pathname + window.location.search;

type PropsEnlace = Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> & {
  a: string;
  /** Marca el enlace como la página actual cuando la ruta coincide. Con
   *  `prefijo`, también cuando la ruta actual cuelga de él (`/admin/pedidos/…`). */
  activo?: "exacto" | "prefijo";
};

export function Enlace({ a, activo, onClick, children, ...resto }: PropsEnlace) {
  const { ubicacion, ir } = useNavegacion();
  const camino = ubicacion.split("?")[0];
  const destino = a.split("?")[0];
  const esActual = activo === "exacto" ? camino === destino
    : activo === "prefijo" ? camino === destino || camino.startsWith(`${destino}/`)
    : false;

  const alHacerClic = (e: MouseEvent<HTMLAnchorElement>) => {
    onClick?.(e);
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    ir(a);
  };

  return (
    <a href={a} onClick={alHacerClic} aria-current={esActual ? "page" : undefined} {...resto}>
      {children}
    </a>
  );
}
