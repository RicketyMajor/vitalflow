/* AC-E3 — any of the 180 hospital ERs, found by name, comuna, region or code, and deep-linkable.
   The index carries no per-week array (asserted in `export_frontend.py`), so this list is the
   whole first paint: 39 KB, not 180 files. */

import { useEffect, useMemo, useState } from "react";
import type { Index } from "./data";

export function Explorer({ index }: { index: Index }) {
  /* AC-N4 — la búsqueda sobrevive la ida y la vuelta. Mirar un hospital y volver obligaba a
     re-escribirla, que es el momento exacto en que alguien abandona un listado de 180.
     `sessionStorage` y no la URL: una lista filtrada compartible no se pidió, y meterla en el hash
     obliga a parsear una query en un router de treinta líneas cuyo valor es que no las tiene. */
  const [q, setQ] = useState(() => sessionStorage.getItem("busqueda") ?? "");
  useEffect(() => { sessionStorage.setItem("busqueda", q); }, [q]);

  const rows = useMemo(() => {
    const needle = fold(q.trim());
    const all = [...index.facilities].sort((a, b) => (a.name ?? "").localeCompare(b.name ?? "", "es"));
    if (!needle) return all;
    return all.filter((f) =>
      fold(`${f.name} ${f.comuna} ${f.region} ${f.code}`).includes(needle));
  }, [index, q]);

  return (
    <section className="pantalla">
      <div className="buscador">
        <label className="nota" htmlFor="q">
          <b>{index.facilities.length} servicios de urgencia hospitalaria</b> temporada {index.season}
        </label>
        <input id="q" type="search" value={q} onChange={(e) => setQ(e.target.value)}
               placeholder="Buscar por hospital, comuna, región o código" autoComplete="off" />
      </div>

      <div className="listado">
        {rows.length === 0 ? (
          <p className="listado__vacio">Ningún servicio coincide con «{q}».</p>
        ) : rows.map((f) => (
          <a key={f.code} href={`#/${f.code}`}>
            <strong>{f.name ?? f.code}</strong>
            <small>{[f.comuna, f.region, `COD ${f.code}`].filter(Boolean).join(" · ")}</small>
            <em>
              {f.surges} {f.surges === 1 ? "alza" : "alzas"}
              {f.alerts > 0 && <> · <b>{f.alerts} {f.alerts === 1 ? "aviso" : "avisos"}</b></>}
            </em>
          </a>
        ))}
      </div>

      <p className="nota nota--pie">
        Los avisos se cuentan a dos semanas, el horizonte que se despliega. La temporada
        {" "}{index.season} ya ocurrió: esta vista pone el resultado al lado del aviso, cosa que el
        producto en operación no puede hacer.
      </p>
    </section>
  );
}

/** Accent- and case-insensitive: nobody types «Región De La Araucanía» with the accents. */
const fold = (s: string) =>
  s.toLowerCase().normalize("NFD").replace(/\p{Diacritic}/gu, "");
