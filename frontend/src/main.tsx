/* Hash routing, ~30 lines and no dependency. Two routes: `#/` the explorer, `#/<code>` a facility.
   Hash rather than history so a static build deploys under any path with no server rewrite, and so
   a facility is deep-linkable — which is the only reason to have a router here at all. */

import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { loadFacility, loadIndex } from "./data";
import type { Facility as F, Index } from "./data";
import { Evidence } from "./Evidence";
import { Explorer } from "./Explorer";
import { Facility } from "./Facility";
import "./styles.css";

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
  const path = useHash().replace(/^\//, "");
  const evidencia = path === "evidencia";

  return (
    <div className="hoja">
      <header className="encabezado">
        <h1>VitalFlow · explorador de servicios</h1>
        <p>
          Demanda respiratoria semanal en las 180 urgencias hospitalarias del país, contra el propio
          umbral de cada servicio. Se puede ver al modelo acertar y se puede ver fallar.
        </p>
        <nav>
          <a href="#/" aria-current={path ? undefined : "page"}>Todos los servicios</a>
          <a href="#/evidencia" aria-current={evidencia ? "page" : undefined}>Evidencia</a>
        </nav>
      </header>

      {evidencia ? <Evidence /> : path ? <FacilityRoute code={path} /> : <ExplorerRoute />}
    </div>
  );
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

createRoot(document.getElementById("root")!).render(
  <StrictMode><App /></StrictMode>,
);
