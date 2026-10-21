/* Piezas que comparten las pantallas del panel (Admin.tsx y AdminProductos.tsx). */

import { useEffect, useState } from "react";
import { ApiError } from "./api";
import { Enlace, useNavegacion } from "./navegacion";
import { rutas } from "./rutas";

/** Nombre legible de los campos que la API cita en `details.fields`. */
const CAMPOS: Record<string, string> = {
  name: "Nombre", description: "Descripción", priceCop: "Precio", categoryId: "Categoría",
  published: "Publicación", size: "Talla", sku: "SKU", initialStock: "Existencias iniciales",
  alt: "Texto alternativo", position: "Posición", file: "Archivo", stockQuantity: "Existencias",
  reason: "Motivo",
};

/** Cómo nombrar lo repetido cuando la API responde CONFLICT. */
const CONFLICTOS: Record<string, string> = {
  size: "la talla", sku: "el SKU", position: "una fotografía en la posición",
};

const campoLegible = (ruta: string) =>
  ruta.split(".").map(p => /^\d+$/.test(p) ? `#${Number(p) + 1}` : CAMPOS[p] ?? p).join(" ")
    .replace(/^variants /, "Talla ");

/** Mensaje para la persona, no para el desarrollador. */
export function mensajeDe(e: unknown): string {
  if (e instanceof ApiError && e.code === "UNAUTHENTICATED") return "Tu sesión expiró. Vuelve a iniciar sesión.";
  if (e instanceof ApiError && e.code === "VALIDATION_ERROR") {
    const campos = (e.details.fields as { field: string; issue: string }[] | undefined) ?? [];
    return campos.length ? campos.map(c => `${campoLegible(c.field)}: ${c.issue}`).join(" · ") : e.message;
  }
  if (e instanceof ApiError && e.code === "CONFLICT" && typeof e.details.field === "string") {
    const que = CONFLICTOS[e.details.field] ?? `un registro con ese valor en ${campoLegible(e.details.field)}:`;
    return `Ya existe ${que} «${String(e.details.value)}».`;
  }
  return e instanceof Error ? e.message : "Ocurrió un error inesperado.";
}

/** Carga datos cuando cambian sus dependencias y descarta respuestas viejas:
 *  si la administradora pasa de la página 2 a la 3 antes de que la 2 llegue,
 *  la respuesta tardía no debe pisar a la nueva. */
export function useCarga<T>(cargar: () => Promise<T>, deps: unknown[]) {
  const [datos, setDatos] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(true);
  useEffect(() => {
    let vigente = true;
    setCargando(true);
    cargar()
      .then(d => { if (vigente) { setDatos(d); setError(null); } })
      .catch(e => { if (vigente) { setDatos(null); setError(mensajeDe(e)); } })
      .finally(() => { if (vigente) setCargando(false); });
    return () => { vigente = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return { datos, setDatos, error, cargando };
}

export function Estado({ cargando, error }: { cargando: boolean; error: string | null }) {
  const { ubicacion } = useNavegacion();
  if (error) {
    return (
      <div className="stock-warning admin-aviso" role="alert">
        {error}{" "}
        {error.startsWith("Tu sesión") && <Enlace a={rutas.ingresar(ubicacion)}>Iniciar sesión</Enlace>}
      </div>
    );
  }
  return cargando ? <div className="admin-placeholder" aria-busy="true"><h2>Cargando…</h2></div> : null;
}
