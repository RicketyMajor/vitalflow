/* La portada — «el país, y una semana».
 *
 *  `context/specs/portada.md`. Superficie de PERSUASIÓN para dos audiencias declaradas: quien juzga
 *  el método, y quien quiere entender el fenómeno antes que el modelo. Las pantallas operativas no
 *  se tocan, y «las renuncias» vive completa en `#/metodo`.
 *
 *  El mundo visual se hereda: mismos tokens, un solo acento, profundidad solo por bordes, mono para
 *  todo dato. Lo único que cambia es la ESCALA.
 *
 *  **AC-P2 — aquí no se escribe ninguna cifra a mano.** Todo número que la página afirma sale de
 *  `data/nacional.json`, de `facilities.json` o del payload del servicio que dibuja, y el refresco
 *  semanal los reescribe. Incluso la correlación del acto 1 se calcula acá, sobre las mismas series
 *  que están en pantalla. Las únicas constantes son de composición (píxeles, duraciones, índices),
 *  el código del servicio de ejemplo — que es una elección de sujeto, no una medición — y `h=2`,
 *  que es una decisión de producto y que AC-P6 obliga a nombrar.
 *
 *  El acento significa lo que significa en las pantallas operativas: **el modelo habló**. Por eso el
 *  acto 1 entero va en tinta y no en azul — la demanda observada no es una afirmación del modelo —
 *  y el azul aparece exactamente una vez, en el acto 3, cuando el modelo efectivamente escribe. */

import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { loadFacility } from "./data";
import type { Facility, Index, Nacional } from "./data";
import { freshness } from "./season";

/* El servicio del acto 3. Elegido por medición sobre los 180 payloads —- 6 avisos, 6 aciertos,
   ninguna falsa alarma, y su semana 35 fue la de rango 1 de toda su temporada -— pero es una
   elección de SUJETO y no una cifra: todo lo que se dice de él se lee de su propio archivo. */
const EJEMPLO = "200717";
const SEMANA_EJEMPLO = 35;

/* La Campaña de Invierno decretada por MINSAL. Un calendario, no una medición: es cuando existe el
   presupuesto de refuerzo, y por eso es lo único que la página superpone a la temporada. */
const CAMPANA = [22, 35] as const;

export function Portada({ nacional, index }: { nacional: Nacional; index: Index }) {
  return (
    <div className="entrada">
      <Pais n={nacional} />
      <Escala n={nacional} />
      <Mecanismo />
      <Que />
      <Acceso n={nacional} index={index} />
    </div>
  );
}

/* ---- acto 1: el país, y la temporada corriendo ----------------------------------------------
   Dieciséis regiones de norte a sur por cincuenta y dos semanas. El scroll barre la temporada y
   las celdas se encienden a su paso. Lo que se ve es que las dieciséis hacen lo mismo al mismo
   tiempo, que es el hallazgo de `03d` dibujado en vez de afirmado.

   Cada región se normaliza contra SU PROPIA semana más alta. La Metropolitana tiene 24 urgencias
   hospitalarias y Arica tiene una: en crudo, una al lado de la otra, esto dibujaría el tamaño de la
   región y no la ola. */

function Pais({ n }: { n: Nacional }) {
  const ref = useSweep<HTMLElement>("--semana", n.semanas.length);
  const r = correlacionMediana(n);
  const alta = semanaMasAlta(n.nacional);

  return (
    <section className="pais" ref={ref} aria-labelledby="pais-t">
      <div className="pais__fijo">
        <p className="entrada__marca">
          VitalFlow<span>Demanda respiratoria · urgencias hospitalarias de Chile</span>
        </p>

        <h1 className="pais__titulo" id="pais-t">
          La temporada respiratoria de Chile no es un peak.
          <span> Es una meseta de ocho meses, y las {n.regiones.length} regiones están en la misma.</span>
        </h1>

        <figure className="pais__figura">
          <div
            className="pais__cinta"
            style={{ "--n": n.semanas.length } as CSSProperties}
            role="img"
            aria-label={
              `Temporada ${n.season}: ${n.regiones.length} regiones de norte a sur por ` +
              `${n.semanas.length} semanas. Cada región contra su propia semana más alta.`
            }
          >
            <span className="pais__ahora" aria-hidden="true" />
            {/* Dos reglas, no un bloque relleno: un relleno queda invisible bajo las celdas
                encendidas y, donde no las hay, se lee como si fuera un dato. Es un calendario
                externo — ni el modelo ni la demanda — así que va en gris y punteado, igual que la
                regla del umbral del acto 3, y nunca en el acento. */}
            <span className="pais__campana" aria-hidden="true" style={{
              "--desde": CAMPANA[0], "--hasta": CAMPANA[1],
            } as CSSProperties}>
              <i>campaña de invierno</i>
            </span>
            {n.regiones.map((reg) => {
              const tope = Math.max(...reg.serie.map((v) => v ?? 0), 1);
              return (
                <div className="pais__fila" key={reg.nombre}>
                  <b title={reg.nombre}>{corto(reg.nombre)}</b>
                  <div className="pais__pista">
                    {reg.serie.map((v, i) => (
                      <i
                        key={i}
                        /* Rule 34: una semana que nadie reportó no es una semana sin atenciones.
                           Hoy no hay ninguna en el payload; se dibuja distinto igual, porque el
                           día que aparezca no puede leerse como demanda cero. */
                        className={v === null ? "pais__celda pais__celda--vacia" : "pais__celda"}
                        style={{ "--w": i + 1, "--v": (v ?? 0) / tope } as CSSProperties}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
            <p className="pais__eje" aria-hidden="true">
              {[1, 13, 26, 39, n.semanas.length].map((w) => (
                <span key={w} style={{ "--w": w, "--n": n.semanas.length } as CSSProperties}>
                  {w}
                </span>
              ))}
            </p>
          </div>

          <figcaption>
            Temporada {n.season}. Cada fila es una región, de Arica a Magallanes; cada columna, una
            semana epidemiológica. La intensidad es la demanda de esa región contra su propia semana
            más alta. Fuente DEIS.
          </figcaption>
        </figure>

        <div className="pais__lectura">
          <p>
            Las {n.regiones.length} regiones se mueven juntas: la correlación mediana entre cada una
            y la curva nacional es <b>{r.toFixed(2)}</b>. Por eso la semana más alta de cada región
            cae en cualquier parte de la meseta — en una meseta el máximo es ruido, no ubicación.
          </p>
          <p>
            La Campaña de Invierno decretada corre entre las semanas {CAMPANA[0]} y {CAMPANA[1]},
            que es cuando existe el presupuesto de refuerzo. La semana más alta del país
            fue la <b>{alta}</b>.
          </p>
        </div>
      </div>
    </section>
  );
}

/* ---- acto 2: la escala --------------------------------------------------------------------
   Una frase, no una fila de tarjetas. Las cifras están a escala de exhibición dentro de la propia
   oración: cuatro tarjetas iguales de número grande y rótulo chico es la plantilla que esta página
   existe para no ser. */

function Escala({ n }: { n: Nacional }) {
  return (
    <section className="escala" aria-labelledby="escala-t">
      <h2 className="oculto" id="escala-t">La escala</h2>
      <p className="escala__frase">
        <Cifra n={n.servicios} /> urgencias hospitalarias, <Cifra n={n.regiones.length} /> regiones,{" "}
        <Cifra n={n.semanas.length} /> semanas medidas — y <Cifra n={n.alzas} /> veces una de ellas
        cruzó <i>su propio</i> umbral.
      </p>
      {/* Prosa, no la capa de anotación: `.nota` es mono, versalita y del tamaño de un pie, y esto
          es una frase de contenido que hay que poder leer de corrido. */}
      <p className="escala__pie">
        El umbral de cada servicio es su percentil 90 histórico, no el de otro hospital. Un hospital
        grande y uno chico se miden cada uno contra su propia vara.
      </p>
    </section>
  );
}

/* ---- acto 3: el mecanismo, sobre un servicio real -------------------------------------------
   Tres tiempos encadenados al scroll: el modelo escribe, pasan dos semanas, la semana ocurre. Es
   la única vez que el acento aparece en toda la página, y aparece donde significa lo que significa
   en las pantallas operativas: el modelo habló. */

function Mecanismo() {
  const [f, setF] = useState<Facility | null>(null);
  useEffect(() => { loadFacility(EJEMPLO).then(setF, () => setF(null)); }, []);
  const ref = useSweep<HTMLElement>("--p", 1);

  if (!f) return <section className="mecanismo mecanismo--vacio" aria-hidden="true" />;

  const i = f.weeks.indexOf(SEMANA_EJEMPLO);
  const origen = SEMANA_EJEMPLO - 2;            // h=2: el origen es dos semanas antes del objetivo
  const rango = f.h2.rank[i];
  const de = f.weeks.length;
  const valor = f.attentions[i];
  const tope = Math.max(...f.attentions.map((v) => v ?? 0), f.p90);

  return (
    <section className="mecanismo" ref={ref} aria-labelledby="mec-t">
      <div className="mecanismo__fijo">
        <h2 className="mecanismo__titulo" id="mec-t">
          Así se ve una semana antes de que ocurra.
        </h2>

        <figure className="mecanismo__figura">
          {/* `--n` es la ÚLTIMA semana, no cuántas hay: la compuerta compara contra números de
              semana, y cinco servicios del panel están puntuados en semanas no contiguas. Acá
              coinciden; en otro servicio no tendrían por qué. */}
          <div className="mecanismo__grafico" style={{
            "--origen": origen, "--n": f.weeks[f.weeks.length - 1],
          } as CSSProperties}>
            <span className="mecanismo__umbral" style={{ "--y": f.p90 / tope } as CSSProperties}>
              <b>umbral del servicio · {f.p90.toLocaleString("es-CL")}</b>
            </span>
            <div className="mecanismo__pista">
              {f.weeks.map((w, k) => (
                <i
                  key={w}
                  className={[
                    "mecanismo__col",
                    w === SEMANA_EJEMPLO ? "mecanismo__col--objetivo" : "",
                    f.h2.alert[k] ? "mecanismo__col--avisada" : "",
                  ].filter(Boolean).join(" ")}
                  style={{ "--w": w, "--v": (f.attentions[k] ?? 0) / tope } as CSSProperties}
                />
              ))}
            </div>
          </div>
          <figcaption>
            {f.name} · temporada {f.season}. Una columna por semana; la regla es el propio umbral
            del servicio. Azul = el modelo avisó. Sobre la regla = ocurrió.
          </figcaption>
        </figure>

        <ol className="mecanismo__tiempos">
          <li>
            <b>Semana {origen}.</b> El modelo lee las últimas semanas de este servicio y de nadie
            más: su anomalía ahora y en los rezagos 1 y 2, su cambio a cuatro semanas, su posición
            estacional y la semana del año.
          </li>
          <li>
            <b>Y escribe.</b> De las {de} semanas de su temporada, la {SEMANA_EJEMPLO} es la que
            queda <b>{rango}ª</b>. No una probabilidad — un orden dentro de sus propias semanas.
            Faltan dos semanas para saber: <i>h=2</i>, el horizonte que se despliega.
          </li>
          <li>
            <b>Semana {SEMANA_EJEMPLO}.</b> Cerró en {valor?.toLocaleString("es-CL")} atenciones,
            sobre su umbral de {f.p90.toLocaleString("es-CL")}. De sus{" "}
            {f.surge.reduce((a, b) => a + b, 0)} alzas de la temporada, este servicio llevaba aviso
            en {f.surge.reduce((a, b, k) => a + (b && f.h2.alert[k] ? 1 : 0), 0)}.
          </li>
        </ol>
      </div>
    </section>
  );
}

/* ---- acto 4: qué es -------------------------------------------------------------------------- */

function Que() {
  return (
    <section className="que" aria-labelledby="que-t">
      <h2 className="que__titulo" id="que-t">Qué es VitalFlow.</h2>
      <p className="que__entrada">
        Un sistema de aviso temprano para las urgencias hospitalarias de Chile. Cada semana estima,
        para cada servicio, qué tan probable es que la semana de dos más adelante supere el propio
        percentil 90 histórico de ese servicio — y entrega esa estimación como un <b>orden</b>, no
        como un porcentaje.
      </p>
      <p className="que__entrada">
        Va dirigido a quien puede hacer algo con dos semanas de aviso: el jefe de urgencia o el
        coordinador de turno. Está construido <b>enteramente con datos públicos</b>, así que
        cualquiera puede reproducir cada número con un navegador.
      </p>
      <ul className="que__palancas">
        <li><b>El plan de contingencia de camas</b><span>corre en 48–72 h</span></li>
        <li><b>La reasignación interna de funciones</b><span>corre en 48–72 h</span></li>
        <li><b>Los turnos espejo</b><span>corre en 48–72 h, con campaña decretada</span></li>
      </ul>
    </section>
  );
}

/* ---- acto 5: las salidas y el sello ----------------------------------------------------------
   AC-I9: nada en pantalla puede envejecer en silencio. Una pantalla en calma y una tubería muerta
   se ven idénticas, y esta línea es lo único que las distingue. */

function Acceso({ n, index }: { n: Nacional; index: Index }) {
  const { dias, viejo } = freshness(n.stamp);
  const [anio, semana] = n.settled_through;
  const vivo = index.facilities.find((f) => f.alerts > 0)?.code ?? EJEMPLO;

  return (
    <section className="acceso" aria-labelledby="acceso-t">
      <h2 className="acceso__titulo" id="acceso-t">Por dónde entrar.</h2>

      <div className="acceso__vias">
        <a className="acceso__via acceso__via--fuerte" href="#/servicios">
          <b>Busca tu urgencia</b>
          <span>Cualquiera de los {n.servicios} servicios: su temporada completa, sus avisos y lo
          que pasó después.</span>
        </a>
        <a className="acceso__via" href={`#/${vivo}/ahora`}>
          <b>La semana que no ha ocurrido</b>
          <span>El pronóstico vivo de una urgencia, sobre una semana que todavía nadie observó.</span>
        </a>
        <a className="acceso__via" href="#/metodo">
          <b>Cómo se construyó</b>
          <span>Las nueve cosas que este proyecto se negó a hacer, cada una con la medición que la
          forzó.</span>
        </a>
        <a className="acceso__via" href="#/evidencia">
          <b>La evidencia</b>
          <span>Lo que se escribió antes de tocar los datos, y lo que volvió. Los fallos en la misma
          tabla que los aciertos.</span>
        </a>
      </div>

      <p className={viejo ? "nota nota--linea sello--viejo" : "nota nota--linea"}>
        Fuente DEIS hasta la <b>semana {semana} de {anio}</b>, la última cerrada ·{" "}
        {viejo
          ? <b>sin actualizar hace {dias} días, el refresco semanal no se ha ejecutado</b>
          : <>actualizado {dias === 0 ? "hoy" : `hace ${dias} ${dias === 1 ? "día" : "días"}`}</>}
        {" "}· todo el sitio es estático y se reconstruye desde el mismo trabajo semanal.
      </p>
    </section>
  );
}

/* ---- instrumentos ---------------------------------------------------------------------------- */

/** Una cifra que cuenta al entrar en vista. Con `prefers-reduced-motion` entra ya escrita.
 *
 *  El valor final es lo que renderiza React, así que sin JS la frase se lee completa y correcta;
 *  la cuenta solo lo reemplaza mientras dura. */
function Cifra({ n }: { n: number }) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || quieto()) return;
    let cuadro = 0;
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      io.disconnect();
      const inicio = performance.now();
      const paso = (t: number) => {
        const p = Math.min(1, (t - inicio) / 1100);
        // Salida exponencial: arranca rápido y se posa en la cifra, nunca la sobrepasa.
        el.textContent = Math.round(n * (1 - (1 - p) ** 4)).toLocaleString("es-CL");
        if (p < 1) cuadro = requestAnimationFrame(paso);
      };
      cuadro = requestAnimationFrame(paso);
    }, { threshold: 0.8 });
    io.observe(el);
    return () => { io.disconnect(); cancelAnimationFrame(cuadro); };
  }, [n]);
  return <b className="escala__cifra" ref={ref}>{n.toLocaleString("es-CL")}</b>;
}

/** Encadena una custom property al progreso del scroll dentro de la propia sección: 0 cuando su
 *  borde superior toca el del viewport, 1 cuando el inferior toca el suyo.
 *
 *  Una sola propiedad manda las 832 celdas del acto 1: el CSS decide por celda, así que React
 *  renderiza una vez y el barrido no vuelve a tocar el DOM.
 *
 *  ponytail: veinte líneas en vez de `motion`. Se instaló, se midió y se sacó — 138 kB de chunk
 *  para tres primitivas (progreso de scroll, `inView`, un contador) que el navegador ya trae. El
 *  resultado en pantalla es el mismo porque el trabajo real lo hace el CSS. Si alguna vez hace
 *  falta una orquestación que esto no alcance, `npm i motion` y de vuelta.
 *
 *  Sin JS la sección se lee entera y quieta: el respaldo de `--semana` en el CSS es la temporada
 *  completa, no una vacía. */
function useSweep<T extends HTMLElement>(prop: string, fin: number) {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (quieto()) { el.style.setProperty(prop, String(fin)); return; }

    let cuadro = 0;
    const medir = () => {
      cuadro = 0;
      const { top, height } = el.getBoundingClientRect();
      const recorrido = height - innerHeight;
      const p = recorrido <= 0 ? 1 : Math.min(1, Math.max(0, -top / recorrido));
      el.style.setProperty(prop, (p * fin).toFixed(3));
    };
    const alMover = () => { if (!cuadro) cuadro = requestAnimationFrame(medir); };

    medir();
    addEventListener("scroll", alMover, { passive: true });
    addEventListener("resize", alMover, { passive: true });
    return () => {
      cancelAnimationFrame(cuadro);
      removeEventListener("scroll", alMover);
      removeEventListener("resize", alMover);
    };
  }, [prop, fin]);
  return ref;
}

const quieto = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

/** "Región Del Libertador Gral. B. O'Higgins" no cabe en una fila de cinta. El nombre completo
    queda en el `title`; nada se pierde, solo se acorta lo que se dibuja. */
function corto(nombre: string) {
  return nombre
    .replace(/^Regi[oó]n\s+(De[l]?\s+)?/i, "")
    .replace(/\s+(del General|y de la)\s.*$/i, "");
}

/** Pearson entre cada región y la curva nacional, y su mediana. Se calcula acá, sobre las mismas
    series que están en pantalla, para que la cifra del acto 1 no sea una constante que alguien
    tenga que acordarse de re-pinear (AC-P2). */
function correlacionMediana(n: Nacional) {
  const rs = n.regiones.map((r) => pearson(r.serie, n.nacional)).filter(Number.isFinite).sort((a, b) => a - b);
  if (!rs.length) return NaN;
  const m = rs.length >> 1;
  return rs.length % 2 ? rs[m] : (rs[m - 1] + rs[m]) / 2;
}

function pearson(a: (number | null)[], b: (number | null)[]) {
  const pares = a.map((v, i) => [v, b[i]] as const).filter(([x, y]) => x !== null && y !== null) as [number, number][];
  const n = pares.length;
  if (n < 3) return NaN;
  const mx = pares.reduce((s, [x]) => s + x, 0) / n;
  const my = pares.reduce((s, [, y]) => s + y, 0) / n;
  let sxy = 0, sxx = 0, syy = 0;
  for (const [x, y] of pares) {
    sxy += (x - mx) * (y - my); sxx += (x - mx) ** 2; syy += (y - my) ** 2;
  }
  return sxy / Math.sqrt(sxx * syy);
}

function semanaMasAlta(serie: (number | null)[]) {
  let mejor = 0, valor = -Infinity;
  serie.forEach((v, i) => { if (v !== null && v > valor) { valor = v; mejor = i; } });
  return mejor + 1;
}
