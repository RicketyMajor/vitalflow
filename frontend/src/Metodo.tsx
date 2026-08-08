/* La portada — «las renuncias».
 *
 *  Una superficie de PERSUASIÓN dentro del mundo ya comprometido ("la pizarra del turno"): mismos
 *  tokens, un solo acento, profundidad solo por bordes. Lo único que cambia es la ESCALA.
 *
 *  El acento se re-apunta aquí igual que en `#/evidencia`, y por la misma razón: en las pantallas
 *  operativas la tinta significa «el modelo habló»; en esta página significa **el horizonte que se
 *  despliega (h=2)** y nada más. Por eso la celda h=2 del muro va en azul de forma permanente y la
 *  selección del deslizador se marca con tinta y una regla, nunca con el acento.
 *
 *  Toda cifra de este archivo está medida y tiene origen en `context/`. Ninguna se inventa, ninguna
 *  se redondea hacia arriba, y el horizonte se nombra cada vez (principio 1 de PRODUCT.md). Las
 *  celdas de h≥4 no llevan número porque el proyecto nunca publicó uno: sabe que es negativo. Un
 *  hueco medido se dibuja como hueco. */

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { Index } from "./data";

/* R² fuera de muestra, dentro de temporada, sobre la anomalía nacional, sin fuga.
   `general/overview.md`: 0.772 a h=1 y 0.450 a h=2; 0.274 a h=3 y negativo desde h=4. */
const HORIZONTE = [
  { h: 1, r2: 0.772, glosa: "Es una medición real de un horizonte que el despliegue no tiene: la semana recién cerrada está 19% completa el día que cierra." },
  { h: 2, r2: 0.450, glosa: "El horizonte del producto. Alcanza para las tres palancas que corren a 48–72 h y para ninguna que necesite un mes." },
  { h: 3, r2: 0.274, glosa: "El último con habilidad medible. Aquí está el muro, y ningún predictor probado lo movió." },
  { h: 4, r2: null,  glosa: "Negativo. A partir de aquí el modelo es peor que no decir nada." },
  { h: 5, r2: null,  glosa: "Negativo. La contaminación, la vigilancia virológica y el vecino más cercano se probaron los tres, y ninguno llegó hasta acá." },
  { h: 6, r2: null,  glosa: "Negativo. El proyecto se reformuló dos veces antes de aceptarlo: nació como pronóstico diario y como alerta a 4–8 semanas." },
];

const ALTO_MAX = 148;   // px, la celda de h=1
const ALTO_HUECO = 26;  // px, el pozo `sin dato` de la cinta

export function Metodo({ index }: { index?: Index }) {
  return (
    <div className="portada">
      <Muro />
      <Renuncias />
      <Queda index={index} />
    </div>
  );
}

/* ---- primer viewport: la renuncia 01, demostrada -------------------------------------------
   No es un encabezado. Es la primera de las nueve, con su medición en pantalla y un instrumento
   que se puede arrastrar: el muro se lee moviéndolo, no leyendo sobre él. */

function Muro() {
  const [h, setH] = useState(2);
  const sel = HORIZONTE[h - 1];
  const ref = useReveal<HTMLElement>();

  return (
    <section className="muro" ref={ref} aria-labelledby="muro-t">
      <p className="muro__marca">
        VitalFlow<span>Demanda respiratoria · urgencias hospitalarias de Chile</span>
      </p>

      <p className="cuenta">01 <i>/</i> 09</p>
      <h1 className="muro__titulo" id="muro-t">
        <span className="tachar">No pronostica más allá de dos semanas.</span>
      </h1>

      <div className="instrumento">
        <div className="instrumento__pista">
          {HORIZONTE.map((c) => (
            <div key={c.h} className={[
              "columna",
              c.r2 === null ? "columna--nula" : "",
              c.h === 2 ? "columna--despliega" : "",
              c.h === h ? "columna--sel" : "",
            ].filter(Boolean).join(" ")}>
              <b style={{ height: `${c.r2 === null ? ALTO_HUECO : Math.round(c.r2 * ALTO_MAX)}px` }} />
              <em>{c.r2 === null ? "—" : c.r2.toFixed(2)}</em>
              <span>h={c.h}</span>
            </div>
          ))}
        </div>

        <label className="instrumento__mando">
          <span className="oculto">Horizonte en semanas</span>
          <input type="range" min={1} max={HORIZONTE.length} step={1} value={h}
                 onChange={(e) => setH(Number(e.target.value))} />
        </label>

        <p className="instrumento__lectura" aria-live="polite">
          <b>h={sel.h}</b>
          <span>{sel.h === 1 ? "una semana" : `${sel.h} semanas`} de anticipación</span>
          <span>R² {sel.r2 === null ? "negativo" : sel.r2.toFixed(3)}</span>
          {sel.h === 2 && <i>el horizonte que se despliega</i>}
        </p>
        <p className="instrumento__glosa">{sel.glosa}</p>
      </div>

      <p className="muro__tesis">
        Es la primera de nueve renuncias. Cada una tiene una medición detrás y ninguna fue una
        preferencia. <b>Lo que queda después de todas ellas es el producto.</b>
      </p>
    </section>
  );
}

/* ---- las ocho restantes ---------------------------------------------------------------------
   Densidad variada a propósito: cinco llevan la medición dibujada, tres la llevan escrita. Una
   procesión de ocho bloques idénticos sería una lista, y una lista no es un argumento. */

type Renuncia = {
  n: string;
  titulo: string;
  medida: ReactNode;
  queda: ReactNode;
};

const RENUNCIAS: Renuncia[] = [
  {
    n: "02",
    titulo: "No muestra una probabilidad.",
    medida: (
      <Figura
        pie="Error de calibración, temporada 2024. Calibrar la empeoró casi cuatro veces."
        cuerpo={
          <div className="calib">
            <div className="calib__fila">
              <b style={{ width: "27.6%" }} />
              <span>0.058</span><i>sin calibrar</i>
            </div>
            <div className="calib__fila calib__fila--peor">
              <b style={{ width: "100%" }} />
              <span>0.210</span><i>calibrada</i>
            </div>
          </div>
        }
      />
    ),
    queda: (
      <>Un <b>orden dentro de las propias semanas del servicio</b> — «1ª de 30» — y nunca un
      porcentaje. La tasa base se mueve de 7.7% a 13.3% entre temporadas, y esa variación
      <i> es</i> lo que el modelo existe para pronosticar: una probabilidad absoluta prospectiva
      es casi inalcanzable, y se midió antes de decirlo.</>
    ),
  },
  {
    n: "03",
    titulo: "No usa colores de triage.",
    medida: (
      <Figura
        pie="En una urgencia chilena el rojo, el amarillo y el verde ya significan otra cosa. Se nombran; no se dibujan."
        cuerpo={
          <div className="vetadas">
            <span className="vetada">Rojo</span>
            <span className="vetada">Amarillo</span>
            <span className="vetada">Verde</span>
            <span className="permitida"><i />Una tinta institucional</span>
          </div>
        }
      />
    ),
    queda: (
      <>Un solo acento, y <b>solo donde el modelo habló</b>. La calma no lleva color en absoluto,
      que es lo correcto cuando el 94% de las semanas-servicio no llevan aviso. El acuerdo y el
      desacuerdo se codifican en <b>geometría</b>: azul = avisamos, sobre la regla = ocurrió.</>
    ),
  },
  {
    n: "04",
    titulo: "No persigue la contaminación.",
    medida: <Cifra valor="< 0.5" unidad="pp de R²" pie="Lo que aporta toda la señal de material particulado, medido en el análisis 03b." />,
    queda: (
      <>Era la hipótesis con la que nació el proyecto. Se midió y se degradó a covariable menor.
      Lo que quedó son <b>seis features, todas del propio servicio</b>: su anomalía estandarizada
      ahora y en los rezagos 1 y 2, su cambio a cuatro semanas, su posición estacional y la semana
      del año.</>
    ),
  },
  {
    n: "05",
    titulo: "No usa un modelo más grande.",
    medida: (
      <Figura
        pie="Costo en recall de eliminar TODAS las features nacionales. La ablación colapsó un diseño de tres etapas a una."
        cuerpo={
          <div className="ablacion">
            <div><b>0.001</b><span>2025</span></div>
            <div><b>0.005</b><span>2024</span></div>
            <p>
              Contra un ruido de corrida a corrida del mismo tamaño. La ola nacional es el promedio
              entre servicios de las mismas anomalías que el clasificador ya tiene.
            </p>
          </div>
        }
      />
    ),
    queda: (
      <><b>Un clasificador sobre seis features.</b> Las tres etapas siguen construidas y medidas en
      el mismo módulo, pero como <i>reporte</i>, nunca como dependencia. `torch` y
      `pytorch-forecasting` se desinstalaron.</>
    ),
  },
  {
    n: "06",
    titulo: "No promete que se pueda contratar refuerzo.",
    medida: <Cifra valor="4–7" unidad="semanas de aviso" pie="Lo que necesita la dotación base. Este aviso llega con 2, contra un muro medido de 3." />,
    queda: (
      <>Tres palancas que sí corren a 48–72 h: el plan de contingencia de camas, la reasignación
      interna y los turnos espejo. <b>La cuarta va tachada en la pantalla</b>, no omitida — el rol
      mensual cierra entre el 20 y el 25 del mes anterior, los calendarios no se cruzan y ningún
      modelo lo arregla. Decirlo es parte del producto.</>
    ),
  },
  {
    n: "07",
    titulo: "No alerta a 446 servicios que sí modela.",
    medida: (
      <Figura
        pie="632 servicios en el panel. Los 446 ambulatorios cargan el 73.7% de las atenciones respiratorias y no tienen camas."
        cuerpo={
          <div className="reparto">
            <div className="reparto__pista">
              <b className="reparto__ambul" style={{ width: "70.6%" }} />
              <b className="reparto__hosp" style={{ width: "29.4%" }} />
            </div>
            <p className="reparto__claves">
              <span><i className="llave" />446 ambulatorios · sin aviso</span>
              <span><i className="llave llave--alertada" />180 urgencias hospitalarias · con aviso</span>
            </p>
          </div>
        }
      />
    ),
    queda: (
      <>En un SAPU o un SAR la consecuencia operativa de un aviso es <b>cero</b>: dotación fija, sin
      boxes extra. Siguen en el panel como filas de entrenamiento y salen de la lista de alerta.
      Restringir el alcance <i>mejoró</i> el producto y su propia vara: recall 0.335 → <b>0.464</b>,
      y la climatología contra la que se mide se debilitó de 2.32 a 2.13.</>
    ),
  },
  {
    n: "08",
    titulo: "No dice que mide saturación.",
    medida: <Cifra valor="0" unidad="denominadores de capacidad" pie="Lo que hay en los datos públicos para dividir la demanda. El proyecto se renombró el 2026-07-29 por esto." />,
    queda: (
      <>Mide <b>demanda contra el propio percentil 90 de cada servicio</b>, que es su propia vara y
      no la de otro hospital. Se midió si una semana sobre ese umbral coincide con tensión real de
      camas: sí, modestamente, <b>+0.060 SD</b> tras auditoría — y la tensión es <b>pediátrica</b>,
      con las salas de adultos en un nulo preciso. Ese último corte es exploratorio replicado, nunca
      pre-registrado, y se etiqueta así cada vez.</>
    ),
  },
  {
    n: "09",
    titulo: "No retira la predicción que falló.",
    medida: (
      <Figura
        pie="Abandono en servicios ambulatorios: el resultado cayó fuera del rango pre-registrado, y del lado contrario."
        cuerpo={
          <div className="fallo">
            <div className="fallo__banda">
              <b className="fallo__rango" />
              <i className="fallo__cero" />
              <u className="fallo__tick" />
            </div>
            <p className="fallo__eje">
              <span>−0.11</span><span>0</span><span>predicho +</span>
            </p>
            <p className="fallo__lectura">
              <b>−0.049 SD</b><span>IC [−0.107, −0.018]</span><span>significativo, en dirección opuesta</span>
            </p>
          </div>
        }
      />
    ),
    queda: (
      <>Sigue publicada, con ambas fechas, <b>en la misma tabla que las que acertaron</b>. Dos cosas
      pesan más que el veredicto y también están escritas: la ventana de replicación
      pre-registrada <b>no existe</b> — el campo lo reporta cero servicios antes de 2020 — y el
      negativo es un efecto de denominador. Una afirmación de este proyecto quedó retirada, tachada
      y con fecha.</>
    ),
  },
];

function Renuncias() {
  return (
    <section className="renuncias" aria-label="Las ocho renuncias restantes">
      {RENUNCIAS.map((r) => <Bloque key={r.n} r={r} />)}
    </section>
  );
}

function Bloque({ r }: { r: Renuncia }) {
  const ref = useReveal<HTMLElement>();
  return (
    <article className="renuncia" ref={ref}>
      <p className="cuenta">{r.n} <i>/</i> 09</p>
      {/* El tachado va sobre un inline con `box-decoration-break: clone`, no sobre un
          pseudo-elemento del bloque: un ::after sólo alcanza la primera línea y se pasa del texto.
          Así cada línea se tacha exactamente hasta donde llega su propia palabra. */}
      <h2 className="renuncia__titulo"><span className="tachar">{r.titulo}</span></h2>
      <div className="renuncia__medida">{r.medida}</div>
      <p className="renuncia__queda">{r.queda}</p>
    </article>
  );
}

/** Un dato dibujado, con su pie. El pie es la fuente; nunca decora. */
function Figura({ cuerpo, pie }: { cuerpo: ReactNode; pie: string }) {
  return (
    <figure className="figura">
      {cuerpo}
      <figcaption>{pie}</figcaption>
    </figure>
  );
}

/** Una sola cifra a escala, para las renuncias cuya medición es un número y no una forma. */
function Cifra({ valor, unidad, pie }: { valor: string; unidad: string; pie: string }) {
  return (
    <figure className="figura figura--cifra">
      <p className="cifra"><b>{valor}</b><span>{unidad}</span></p>
      <figcaption>{pie}</figcaption>
    </figure>
  );
}

/* ---- lo que queda ---------------------------------------------------------------------------
   El cierre se ancla en el número más incómodo del proyecto, no en el mejor. Un evaluador que
   llegue hasta acá se lleva el margen honesto a h=2, no la cifra de titular a h=1. */

function Queda({ index }: { index?: Index }) {
  const ref = useReveal<HTMLElement>();
  return (
    <section className="queda" ref={ref} aria-labelledby="queda-t">
      <h2 className="queda__titulo" id="queda-t">Lo que quedó en pie.</h2>

      <p className="queda__entrada">
        Un clasificador sobre seis features, en <b>180 urgencias hospitalarias</b>, avisando con dos
        semanas contra el propio umbral histórico de cada servicio. Contra la climatología
        estacional en la temporada 2026 sellada — pre-registrada y abierta una sola vez — el margen
        a h=2 fue <b>2.69×</b> sobre un piso exigido de 2×.
      </p>

      <div className="margen">
        <p className="margen__rotulo">
          Y este es el número que no conviene: margen en <b>recall de inicio</b> sobre el calendario
          estacional, a h=2, el horizonte que efectivamente se despliega
        </p>
        <div className="margen__fila">
          <div><b>+0.00</b><span>2024</span><i>empate exacto</i></div>
          <div><b>+0.09</b><span>2025</span><i>gana</i></div>
          <div><b>+0.03</b><span>2026</span><i>gana</i></div>
        </div>
        <p className="margen__pie">
          Las cifras que se citan de este proyecto — 0.22 contra 0.13 del calendario — son de h=1,
          un horizonte que el despliegue no tiene. Ambas son correctas y solo una se despliega.
          Contra la persistencia, una regla de cero parámetros, el modelo gana <b>6 de 6</b> celdas.
        </p>
      </div>

      <div className="salidas">
        <a className="salida salida--fuerte" href="#/129103">
          <b>El fallo</b>
          <span>Servicio 129103 · tres alzas y ningún aviso. La pantalla existe para mostrarlo.</span>
        </a>
        <a className="salida" href="#/129104/ahora">
          <b>La semana que no ha ocurrido</b>
          <span>El pronóstico vivo de una urgencia, sobre una semana que todavía nadie observó.</span>
        </a>
        <a className="salida" href="#/servicios">
          <b>Los 180 servicios</b>
          <span>Cualquiera de ellos, su temporada completa, sus avisos y lo que pasó después.</span>
        </a>
        <a className="salida" href="#/evidencia">
          <b>La evidencia</b>
          <span>Lo escrito antes de tocar los datos, y lo que volvió. Los fallos en la misma tabla.</span>
        </a>
      </div>

      <p className="ausencia">
        <b>Ninguna persona que trabaje en una urgencia hospitalaria ha leído esta interfaz
        todavía.</b> Es la suposición más riesgosa del diseño — si un ordinal es accionable o
        inerte para un coordinador de turno — y ninguna medición puede resolverla. Está declarada
        como ausencia en la especificación en vez de aparecer como una conversación que no ocurrió.
      </p>

      {index && (
        <p className="nota nota--linea">
          Fuente DEIS hasta la semana {index.settled_through[1]} de {index.settled_through[0]},
          la última cerrada · exportado el {index.stamp} · todo el sitio es estático y se
          reconstruye desde el mismo trabajo semanal.
        </p>
      )}
    </section>
  );
}

/* Una entrada, orquestada, que revela el tachado de cada renuncia. El contenido es visible por
   defecto: la clase solo dispara el trazo, así que sin JS o con `prefers-reduced-motion` la página
   se lee entera igual. */
function useReveal<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { el.classList.add("vista"); io.disconnect(); }
    }, { rootMargin: "0px 0px -20% 0px" });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return ref;
}
