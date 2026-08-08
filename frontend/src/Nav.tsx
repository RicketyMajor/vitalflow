/* Orientación, y nada más. Vive aparte de `main.tsx` porque son cuatro componentes con estado
   propio —un observador centinela, `localStorage`, `sessionStorage`— que cambian juntos y por las
   mismas razones.

   ⚠ LA CLASE ES `.barra-sitio`, NO `.barra`. `.barra` es la fila superior del tablero
   (`styles.css:205`), y el 2026-08-06 una clase nueva ya chocó en silencio con ella. Se verificó
   por grep antes de escribir esto, no después.

   El agujero que esto cierra estaba medido: `main.tsx` suprimía el encabezado en `#/` y `#/metodo`
   con `const propio = portada || metodo`, así que las dos superficies narrativas no tenían salida
   persistente, ni marca que llevara a casa, ni vuelta atrás. Sus únicas puertas estaban al final
   de ~8 viewports. */

import { useEffect, useRef, useState } from "react";

const RUTAS = [
  { href: "#/servicios", texto: "Servicios" },
  { href: "#/metodo", texto: "Método" },
  { href: "#/evidencia", texto: "Evidencia" },
] as const;

/** La barra. En las superficies narrativas NO está sobre la tesis: aparece cuando el lector deja
 *  el primer viewport, que es exactamente la objeción registrada el 2026-08-07 («un preámbulo
 *  sobre una tesis es un preámbulo») respetada en vez de ignorada.
 *
 *  El disparo va por un CENTINELA observado, no por un listener de scroll: es el mismo motivo por
 *  el que `useReveal` dejó de escuchar scroll. */
export function Barra({ narrativa }: { narrativa: boolean }) {
  const [visible, setVisible] = useState(!narrativa);
  const centinela = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!narrativa) { setVisible(true); return; }
    setVisible(false);
    const el = centinela.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => setVisible(!e.isIntersecting));
    io.observe(el);
    return () => io.disconnect();
  }, [narrativa]);

  return (
    <>
      {narrativa && <div className="barra-sitio__centinela" ref={centinela} aria-hidden="true" />}
      <div className={visible ? "barra-sitio barra-sitio--vista" : "barra-sitio"}>
        <a className="barra-sitio__marca" href="#/">VitalFlow</a>
        <nav aria-label="Secciones">
          {RUTAS.map((r) => (
            <a key={r.href} href={r.href}
               aria-current={location.hash === r.href ? "page" : undefined}>{r.texto}</a>
          ))}
        </nav>
        <Tema />
      </div>
    </>
  );
}

/* El control de tema, movido acá desde `main.tsx`. Era el único elemento `position: fixed` de todo
   el sitio y no tenía familia; ahora vive en la barra, que es su familia.
   Texto y no un sol y una luna: este mundo no tiene sistema de iconos en ninguna superficie — es
   texto, mono y geometría — e inventar uno para un solo control sería el disfraz de siempre.

   No se escribe atributo hasta que el visitante elige, así que el default sin tocar sigue siendo la
   preferencia del sistema operativo y el bloque `prefers-color-scheme` sigue mandando. AC-P9. */
export function Tema() {
  const [tema, setTema] = useState<string | null>(() => localStorage.getItem("tema"));

  useEffect(() => {
    const raiz = document.documentElement;
    if (tema) raiz.setAttribute("data-theme", tema);
    else raiz.removeAttribute("data-theme");
  }, [tema]);

  const oscuro = tema ? tema === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;

  return (
    <button type="button" className="barra-sitio__tema"
      aria-label={oscuro ? "Cambiar a tema claro" : "Cambiar a tema oscuro"}
      onClick={() => {
        const siguiente = oscuro ? "light" : "dark";
        localStorage.setItem("tema", siguiente);
        setTema(siguiente);
      }}>
      {oscuro ? "claro" : "oscuro"}
    </button>
  );
}

/** La vuelta al listado. La nav de la barra ya llega a `#/servicios`, pero «volver» y «navegar a»
    no son el mismo gesto: uno deshace, el otro elige. AC-N3. */
export function Volver() {
  return <a className="volver" href="#/servicios">← Todos los servicios</a>;
}

/** El conmutador entre las dos pantallas del MISMO servicio. Es el único par donde alguien se
 *  pierde de verdad — mismo hospital, epistemología opuesta — y hasta ahora lo único que las unía
 *  era una línea de prosa al final de cada una.
 *
 *  Rotulado por LA PREGUNTA QUE CADA UNA RESPONDE, no por «retrospectiva / en vivo»: esos dos
 *  rótulos describen la implementación y no le dicen nada a quien llega. */
export function Par({ code, aqui }: { code: string; aqui: "temporada" | "ahora" }) {
  return (
    <div className="par" role="group" aria-label="Dos vistas de este servicio">
      <a href={`#/${code}`} aria-current={aqui === "temporada" ? "page" : undefined}>
        <b>Qué pasó</b><span>la temporada cerrada, con lo ocurrido al lado de lo avisado</span>
      </a>
      <a href={`#/${code}/ahora`} aria-current={aqui === "ahora" ? "page" : undefined}>
        <b>Qué viene</b><span>la semana que todavía nadie observó</span>
      </a>
    </div>
  );
}
