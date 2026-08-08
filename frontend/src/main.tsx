/* Hash routing, ~30 lines and no dependency. `#/` the portada, `#/metodo` the nine refusals,
   `#/servicios` the explorer, `#/<code>` a facility, `#/<code>/ahora` its live forecast,
   `#/evidencia` the ledger.
   Hash rather than history so a static build deploys under any path with no server rewrite, and so
   a facility is deep-linkable — which is the only reason to have a router here at all.

   `#/` changed owner on 2026-08-07 (`specs/portada.md`). «Las renuncias» moved to `#/metodo`
   unchanged; no other route moved, so no deep link that ever existed is broken. */

import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { loadFacility, loadIndex, loadLive, loadNacional } from "./data";
import type { Facility as F, Index, Live as L, Nacional } from "./data";
import { Evidence } from "./Evidence";
import { Explorer } from "./Explorer";
import { Facility } from "./Facility";
import { Live } from "./Live";
import { Metodo } from "./Metodo";
import { Portada } from "./Portada";
import { freshness } from "./season";
import "./styles.css";
import "./portada.css";

function useHash() {
  const [hash, setHash] = useState(() => location.hash.slice(1) || "/");
  useEffect(() => {
    const on = () => { setHash(location.hash.slice(1) || "/"); scrollTo(0, 0); };
    addEventListener("hashchange", on);
    return () => removeEventListener("hashchange", on);
  }, []);
  return hash;
}

/** One in-flight request per route change; a stale response never lands. */
function useAsync<T>(fn: () => Promise<T>, key: string) {
  const [state, setState] = useState<{ data?: T; error?: unknown }>({});
  useEffect(() => {
    let live = true;
    setState({});
    fn().then((d) => live && setState({ data: d }), (e) => live && setState({ error: e }));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return state;
}

function App() {
  // `#/<code>` the finished season · `#/<code>/ahora` the week that has not happened.
  const [head, tail] = useHash().replace(/^\//, "").split("/");
  const evidencia = head === "evidencia";
  const servicios = head === "servicios";
  const metodo = head === "metodo";
  const portada = !head;
  // Both narrative surfaces own their first viewport and carry their own marca and stamp, so the
  // shared masthead is suppressed on them: a preamble above a thesis is a preamble.
  const propio = portada || metodo;
  // Shares the promise `ExplorerRoute` uses — `data.ts` caches by path, so this costs one cached
  // 39 KB index across every route. The stamp belongs on all of them: a stale reading is not less
  // stale for having been reached through a facility link.
  const { data: index } = useAsync<Index>(loadIndex, "index");

  // `hoja--portada` is the 1120px measure «las renuncias» was composed against; it moved with the
  // surface. The new portada is full-bleed and owns its own widths.
  return (
    <div className={portada ? "hoja hoja--entrada" : metodo ? "hoja hoja--portada" : "hoja"}>
      <Tema />
      {!propio && (
        <header className="encabezado">
          <h1><a href="#/">VitalFlow</a> · explorador de servicios</h1>
          <p>
            Demanda respiratoria semanal en las 180 urgencias hospitalarias del país, contra el propio
            umbral de cada servicio. Se puede ver al modelo acertar y se puede ver fallar.
          </p>
          {index && <Sello index={index} />}
          <nav>
            <a href="#/">Portada</a>
            <a href="#/servicios" aria-current={servicios ? "page" : undefined}>Todos los servicios</a>
            <a href="#/metodo">Método</a>
            <a href="#/evidencia" aria-current={evidencia ? "page" : undefined}>Evidencia</a>
          </nav>
        </header>
      )}

      {portada ? <PortadaRoute />
        : metodo ? <MetodoRoute />
        : evidencia ? <EvidenceRoute />
        : servicios ? <ExplorerRoute />
        : tail === "ahora" ? <LiveRoute code={head} />
        : <FacilityRoute code={head} />}
    </div>
  );
}

/* The theme control. `styles.css` has declared `:root[data-theme="dark"]` and `[="light"]` since
   2026-08-02 and NOTHING had ever written the attribute — the selectors were dead for five days.
   AC-P9.

   No attribute is written until the visitor chooses one, so the untouched default stays the
   operating system's preference and the `prefers-color-scheme` block keeps ruling. Text rather
   than a sun and a moon: this world has no icon system at all — it is text, monospace and
   geometry — and inventing one for a single control would be the costume the craft floor warns
   about. */
function Tema() {
  const [tema, setTema] = useState<string | null>(() => localStorage.getItem("tema"));

  useEffect(() => {
    const raiz = document.documentElement;
    if (tema) raiz.setAttribute("data-theme", tema);
    else raiz.removeAttribute("data-theme");
  }, [tema]);

  const oscuro = tema ? tema === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;

  return (
    <button
      type="button"
      className="tema"
      aria-label={oscuro ? "Cambiar a tema claro" : "Cambiar a tema oscuro"}
      onClick={() => {
        const siguiente = oscuro ? "light" : "dark";
        localStorage.setItem("tema", siguiente);
        setTema(siguiente);
      }}
    >
      {oscuro ? "claro" : "oscuro"}
    </button>
  );
}

/* AC-I9 — the trust mechanism the silent-facility audit asked for. A calm screen and a dead
   pipeline look identical, and until this line existed nothing on screen could tell them apart.
   No accent: the institutional blue means "the model spoke", and staleness is not a model output. */
function Sello({ index }: { index: Index }) {
  const [anio, semana] = index.settled_through;
  const { dias, viejo } = freshness(index.stamp);
  return (
    <p className={viejo ? "nota sello sello--viejo" : "nota sello"}>
      {/* "Fuente DEIS", not "datos": the served season is 2025 while the snapshot reaches 2026,
          and a line that omitted the source would contradict the season the screen is showing. */}
      Fuente DEIS hasta la <b>semana {semana} de {anio}</b>, la última cerrada ·{" "}
      {viejo
        ? <b>sin actualizar hace {dias} días, el refresco semanal no se ha ejecutado</b>
        : <>actualizado {dias === 0 ? "hoy" : `hace ${dias} ${dias === 1 ? "día" : "días"}`}</>}
    </p>
  );
}

/** AC-P12: the portada's first paint is the index plus the national payload, and one facility for
    the mechanism act. Never the 180 — the same budget AC-E6 fixed for the explorer. */
function PortadaRoute() {
  const { data: nacional } = useAsync<Nacional>(loadNacional, "nacional");
  const { data: index } = useAsync<Index>(loadIndex, "index");
  if (!nacional || !index) return <p className="cargando">Cargando…</p>;
  return <Portada nacional={nacional} index={index} />;
}

/** `#/metodo` pasó a leer sus cifras de cobertura del export (item G, clase A), así que necesita
    el payload nacional además del índice. **No agrega una petición al presupuesto**: `data.ts`
    cachea por ruta y `#/` ya trae los mismos dos archivos, así que llegar por cualquiera de los dos
    caminos cuesta lo mismo. AC-G4. */
function MetodoRoute() {
  const { data: nacional } = useAsync<Nacional>(loadNacional, "nacional");
  const { data: index } = useAsync<Index>(loadIndex, "index");
  if (!nacional || !index) return <p className="cargando">Cargando…</p>;
  return <Metodo index={index} nacional={nacional} />;
}

/** `#/evidencia` lee su ÁMBITO del export por la misma razón que `#/metodo` (item G, clase A).
    Sus rangos pre-registrados y sus efectos auditados NO: nada los recomputa, así que siguen
    siendo literales fechados. */
function EvidenceRoute() {
  const { data: nacional } = useAsync<Nacional>(loadNacional, "nacional");
  if (!nacional) return <p className="cargando">Cargando…</p>;
  return <Evidence nacional={nacional} />;
}

function ExplorerRoute() {
  const { data, error } = useAsync<Index>(loadIndex, "index");
  if (error) return <p className="cargando">No se pudo leer el índice de servicios.</p>;
  if (!data) return <p className="cargando">Cargando…</p>;
  return <Explorer index={data} />;
}

/** AC-E6: the facility file is fetched here, on selection — never as part of the first paint. */
function FacilityRoute({ code }: { code: string }) {
  const { data, error } = useAsync<F>(() => loadFacility(code), code);
  if (error) return <p className="cargando">No hay datos para el servicio {code}.</p>;
  if (!data) return <p className="cargando">Cargando servicio {code}…</p>;
  return <Facility f={data} />;
}

/** The live screen. Its own route over its own file, not a mode on the facility screen: the two
    views answer different questions and a toggle between them is how one of them starts lying. */
function LiveRoute({ code }: { code: string }) {
  const { data, error } = useAsync<L>(() => loadLive(code), `live-${code}`);
  if (error) return <p className="cargando">No hay pronóstico publicado para el servicio {code}.</p>;
  if (!data) return <p className="cargando">Cargando servicio {code}…</p>;
  return <Live f={data} />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode><App /></StrictMode>,
);
