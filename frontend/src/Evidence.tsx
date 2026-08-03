/* #/evidencia — the route that carries the product's caveat.
 *
 * THESIS: this is a register of predictions and their outcomes, not a results page. Every finding
 * appears the way it was produced — what was written down before the data was touched, then what
 * came back — and the predictions that FAILED sit in the same table as the ones that held. It
 * refuses the category default: a metrics hero with a big accuracy number and supporting stats.
 * OWN-WORLD: "la pizarra del turno", unchanged and not reopened. Board surfaces on the pale
 * green-cold wall, borders only, mono for every datum. The single institutional ink is re-pointed
 * for this surface: here it marks the OPERATIONAL horizon (h=2) and nothing else, so one blue
 * thread runs the page tracing the numbers that actually ship.
 * STORY: the reader learns the horizon that deploys is two weeks, sees the honest margin there
 * (+0.00 / +0.09 / +0.03), then reads a sealed test that passed on a metric the next section
 * disowns, and leaves able to tell which of this project's numbers are the product's.
 * FIRST VIEWPORT: no PERFORMANCE number above the fold. The horizon statement, the settling facts
 * that force it, then the h=2 margin table — the thin figure first, never the impressive one.
 * FORM: pre-registration beside outcome; candidate 3 of the ordered structure list, staged as a
 * ledger of fichas where each row's plausible range is drawn and the outcome is a tick on it.
 * Seed key 06c17f13, surface scope, Read mode.
 *
 * Every figure is quoted from `docs/vitalflow-project.md` §9.1/§9.1b, `2026-sealed-holdout.md` and
 * `rem20-construct-validity.md`. They are published results, not runtime data — this file is the
 * one place to update them. **They print the digits that were measured**; the project's rule is
 * that no conclusion may rest on the third one, not that the third one be hidden. */

/** Where the outcome falls on its own predicted range. The band occupies the middle 60% of the
 *  track so a prediction that missed still lands on screen — which is the point of drawing it. */
const pos = (lo: number, hi: number, v: number) =>
  Math.min(0.98, Math.max(0.02, 0.2 + (0.6 * (v - lo)) / (hi - lo)));

const MARGEN_H2 = [
  { season: "2024", cal: "0.117", model: "0.117", margin: "+0.00", note: "empate exacto" },
  { season: "2025", cal: "0.128", model: "0.217", margin: "+0.09", note: "" },
  { season: "2026", cal: "0.131", model: "0.162", margin: "+0.03", note: "temporada sellada" },
];

/* The seven quantities the pre-registration named, all seven of them. Four missed their range. */
const HOLDOUT = [
  { q: "Tasa base, semanas 1–28", pred: "0.10", range: "0.04 – 0.17", got: "0.055",
    lo: 0.04, hi: 0.17, p: 0.10, v: 0.055, verdict: "dentro, en el extremo bajo", key: false },
  { q: "Gasto realizado, h=1", pred: "11%", range: "8% – 18%", got: "6.0%",
    lo: 8, hi: 18, p: 11, v: 6.0, verdict: "bajo el rango, no falsificada", key: false },
  { q: "Lift a h=2 — resultado primario", pred: "4.0", range: "3.0 – 5.0", got: "5.19",
    lo: 3, hi: 5, p: 4, v: 5.19, verdict: "sobre el rango · cumple AC-H1", key: true },
  { q: "Lift a h=1", pred: "5.0", range: "4.0 – 6.5", got: "8.31",
    lo: 4, hi: 6.5, p: 5, v: 8.31, verdict: "falsificada, sobre 7.5", key: false, falla: true },
  { q: "Recall a h=1", pred: "0.55", range: "0.45 – 0.70", got: "0.500",
    lo: 0.45, hi: 0.70, p: 0.55, v: 0.500, verdict: "dentro", key: false },
  { q: "Lift del calendario, h=1", pred: "2.5", range: "2.0 – 3.0", got: "1.98",
    lo: 2, hi: 3, p: 2.5, v: 1.98, verdict: "marginalmente por debajo", key: false, falla: true },
  { q: "Servicios silenciosos de 180, h=1", pred: "25", range: "10 – 50", got: "72",
    lo: 10, hi: 50, p: 25, v: 72, verdict: "sobre el rango", key: false, falla: true },
];

const ONSET = [
  { season: "2024", h: 1, cal: "0.139", model: "0.109", pers: "0.000" },
  { season: "2024", h: 2, cal: "0.117", model: "0.117", pers: "0.061" },
  { season: "2025", h: 1, cal: "0.121", model: "0.173", pers: "0.000" },
  { season: "2025", h: 2, cal: "0.128", model: "0.217", pers: "0.200" },
  { season: "2026", h: 1, cal: "0.137", model: "0.221", pers: "0.046" },
  { season: "2026", h: 2, cal: "0.131", model: "0.162", pers: "0.108" },
];

const TRAMPAS = [
  ["Nombra el horizonte, siempre.",
   "h=1 es una medición; h=2 es el producto. Las cifras que se citan — recall de alzas nuevas 0.221 contra 0.137 del calendario — son de h=1."],
  ["Lee alzas nuevas, no el recall agregado.",
   "El agregado es entre 52% y 64% continuación, y una regla de cero parámetros le gana ahí."],
  ["Compara solo a gasto igualado.",
   "El lift sube a medida que se alerta menos. Una tabla sin igualar el gasto revirtió una conclusión dos veces en una misma sesión."],
  ["Entre temporadas, usa el margen y no el lift.",
   "lift = precisión ÷ tasa base, y la tasa base es la severidad de la temporada que el modelo existe para pronosticar."],
  ["Ninguna conclusión descansa en la tercera cifra.",
   "Las tablas imprimen lo que se midió. Pero el ajuste, aunque reproducible desde el 2026-07-30, sigue siendo sensible: permutar el orden de las filas mueve el lift de 2026 a h=1 entre 7.94 y 8.31. Una afirmación que descansaba en 0.002 no sobrevivió a eso."],
];

export function Evidence() {
  return (
    <section className="pliego">
      <header className="pliego__tramo">
        <h2 className="pliego__titulo pliego__titulo--pagina">Evidencia</h2>
        <p className="pliego__entrada">
          Lo que este sistema puede sostener y lo que no, ordenado por lo que pesa. Cada resultado
          aparece como se produjo: primero lo que quedó escrito <em>antes</em> de tocar los datos,
          después lo que volvió. Las predicciones que fallaron están en la misma tabla que las que se
          cumplieron.
        </p>
        <p className="nota nota--linea">
          <b>Las cifras subrayadas</b> marcan el horizonte que se despliega donde más importa · están
          enlazadas entre sí
        </p>
      </header>

      {/* ---- 1. the horizon leads. No performance number above it. ---------- */}
      <section className="pliego__tramo">
        <h3 className="pliego__titulo">El horizonte que se despliega es de dos semanas</h3>
        <p>
          Una semana DEIS está cerca del <strong>19% completa el día que cierra</strong> y 97.8%
          asentada a los siete días. El origen de servicio es, entonces, la última semana cerrada —
          W−1 — y eso deja <span className="despliega">h=2</span> como el único horizonte que existe
          en operación.
        </p>
        <p>
          Las cifras que este proyecto citó desde el principio son de <strong>h=1</strong>:
          mediciones correctas de un horizonte que el despliegue no tiene. Este es el margen del
          horizonte que sí tiene, sobre <em>alzas nuevas</em> — semanas que cruzan el umbral sin
          venir cruzándolo — y a gasto igualado.
        </p>

        <figure className="registro__caja">
          <table className="registro">
            <caption>Recall de alzas nuevas a h=2 · gasto igualado · 180 urgencias hospitalarias</caption>
            <thead>
              <tr>
                <th scope="col">Temporada</th>
                <th scope="col">Calendario estacional</th>
                <th scope="col">Este modelo</th>
                <th scope="col">Margen</th>
              </tr>
            </thead>
            <tbody>
              {MARGEN_H2.map((r) => (
                <tr key={r.season}>
                  <th scope="row">{r.season}{r.note && <i> · {r.note}</i>}</th>
                  <td>{r.cal}</td>
                  <td className="vuelta">{r.model}</td>
                  <td><span className="despliega">{r.margin}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </figure>

        <p className="pie">
          La celda de 2026 se mueve entre 0.154 y 0.162 al permutar el orden de las filas, así que
          ese +0.03 es realmente <strong>+0.02 a +0.03</strong>.
        </p>
        <p className="remate">
          El resumen honesto del horizonte operativo: el modelo es claramente mejor que el calendario
          estacional en <strong>una</strong> de tres temporadas, <strong>empata</strong> en otra y{" "}
          <strong>va modestamente adelante</strong> en la sellada. Nada de lo que sigue retira esto.
        </p>
      </section>

      {/* ---- 2. the sealed holdout, as a prediction/outcome ledger ---------- */}
      <article className="ficha">
        <div className="ficha__cabeza">
          <h3>Holdout sellado · temporada 2026</h3>
          <span className="veredicto">4 de 4 criterios cumplidos</span>
        </div>
        <div className="ficha__cuerpo">
          <p className="protocolo">
            <span><b>Temporada</b> 2026 · semanas 1–28</span>
            <span><b>Ámbito</b> 180 urgencias hospitalarias</span>
            <span><b>Entrenamiento</b> 2022–2025</span>
            <span><b>Corte calibrado en</b> 2025</span>
            <span><b>Resultado primario</b> lift a h=2</span>
            <span><b>Corre</b> una sola vez</span>
          </p>
          <p>
            2026 no fue consultada por ninguna decisión: ni las variables, ni la ventana de
            climatología, ni la regla de presupuesto. Las siete expectativas de abajo se escribieron
            antes de tocar el archivo, con sus condiciones de falsación. <strong>Cuatro erraron su
            rango.</strong>
          </p>

          <figure className="registro__caja">
            <table className="registro">
              <caption>Lo que se predijo · dónde cayó · lo que volvió</caption>
              <thead>
                <tr>
                  <th scope="col">Cantidad</th>
                  <th scope="col" className="antes">Se predijo</th>
                  <th scope="col" className="antes">Rango plausible</th>
                  <th scope="col"><span className="vsr">Dónde cayó</span></th>
                  <th scope="col">Volvió</th>
                  <th scope="col">Veredicto</th>
                </tr>
              </thead>
              <tbody>
                {HOLDOUT.map((r) => (
                  <tr key={r.q}>
                    <th scope="row">{r.q}</th>
                    <td className="antes">{r.pred}</td>
                    <td className="antes">{r.range}</td>
                    <td>
                      <span className={`rango${r.falla ? " rango--fuera" : ""}`}
                            style={{ "--v": pos(r.lo, r.hi, r.v),
                                     "--p": pos(r.lo, r.hi, r.p) } as React.CSSProperties}
                            role="img"
                            aria-label={`Rango ${r.range}; volvió ${r.got}: ${r.verdict}`}>
                        <i className="rango__banda" />
                        <i className="rango__previo" />
                        <i className="rango__marca" />
                      </span>
                    </td>
                    <td className="vuelta">
                      {r.key ? <span className="despliega">{r.got}</span> : r.got}
                    </td>
                    <td className={r.falla ? "falla" : ""}>{r.verdict}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </figure>
          <p className="pie">
            La banda es el rango plausible; la marca tenue, el valor puntual que se predijo; la marca
            sólida, lo que volvió. Fuera de la banda significa que la expectativa erró.
          </p>

          <p>
            Los cuatro criterios de aceptación se cumplieron igual. El primario pedía superar al
            calendario estacional por al menos el doble sobre filas idénticas:{" "}
            <span className="despliega">lift 5.19 contra 1.92, margen 2.69×</span>, contra un piso de
            2×.
          </p>
          <p className="remate">
            <strong>Y el mecanismo pre-registrado era incorrecto, que es el hallazgo.</strong> El
            pre-registro razonaba que un corte calibrado en la tranquila 2025 y aplicado a una
            ventana cargada de invierno debía sobre-alertar: el gasto subiría y el lift bajaría.
            Dejó escrito que un lift sobre 7.06 significaría que ese razonamiento estaba mal. El
            gasto <em>bajó</em> a 6.0% y el lift <em>subió</em> a 8.31, porque las semanas 1–28 de
            2026 resultaron <strong>más tranquilas que la tranquila 2025</strong> — tasa base 0.055
            contra 0.070. La severidad de la temporada se comió el efecto de truncar la ventana.
          </p>
          <p>
            De ahí sale la regla que gobierna cómo se lee todo lo demás:{" "}
            <code>lift = precisión ÷ tasa base</code>, y la tasa base es exactamente la severidad
            que el modelo existe para pronosticar. <strong>El lift no es comparable entre
            temporadas.</strong> Lo comparable es el margen.
          </p>
          <p className="advertencia">
            <b>Y hay algo peor que un mecanismo equivocado.</b> El resultado primario de este
            pre-registro era el <em>lift agregado</em>, y la sección siguiente muestra que esa
            métrica estaba midiendo la mitad fácil del problema. El criterio se cumplió; el criterio
            era el equivocado. Las dos cosas son ciertas y la segunda importa más.
          </p>
        </div>
      </article>

      {/* ---- 3. the easy half ---------------------------------------------- */}
      <section className="pliego__tramo">
        <h3 className="pliego__titulo">La métrica estaba midiendo la mitad fácil</h3>
        <p>
          Entre <strong>52% y 64%</strong> de las semanas sobre el umbral son <em>continuación</em>:
          el servicio ya estaba sobre su p90 la semana anterior. Un coordinador ve un alza en curso
          desde la sala de espera. Un <em>alza nueva</em> — la semana que cruza el umbral sin venir
          cruzándolo — es para lo que existe un sistema de alerta temprana, y es la mitad difícil.
        </p>
        <p>
          <strong>Sobre la métrica agregada que este proyecto reportó desde el día uno, una regla de
          cero parámetros le gana al modelo:</strong> «avisa la próxima semana si este servicio está
          sobre su p90 esta semana». En la temporada sellada, a h=2, esa regla marca recall 0.315 y
          precisión 0.333 contra 0.282 y 0.284 del modelo, gastando menos. Que una regla sin
          entrenamiento gane significa que <em>la métrica está mal</em>, no que el modelo no sirva —
          y separar el conjunto de verdad muestra por qué.
        </p>

        <figure className="registro__caja">
          <table className="registro">
            <caption>Recall de alzas nuevas a gasto igualado · cada regla recibe el mismo número de avisos</caption>
            <thead>
              <tr>
                <th scope="col">Temporada</th>
                <th scope="col">h</th>
                <th scope="col">Calendario</th>
                <th scope="col">Este modelo</th>
                <th scope="col">Persistencia</th>
              </tr>
            </thead>
            <tbody>
              {ONSET.map((r) => (
                <tr key={`${r.season}-${r.h}`} className={r.h === 2 ? "fila--opera" : ""}>
                  <th scope="row">{r.season}</th>
                  <td>{r.h === 2 ? <span className="despliega">2</span> : "1"}</td>
                  <td>{r.cal}</td>
                  <td className="vuelta">{r.model}</td>
                  <td>{r.pers}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </figure>

        <p className="pie">
          Gana al calendario en <strong>4 de 6</strong> celdas, empata 2024 h=2 y pierde 2024 h=1.
          Gana a la persistencia en <strong>6 de 6</strong>. La persistencia marca 0.000 a h=1 por
          construcción: no puede señalar un alza que todavía no ha empezado, así que su victoria en
          el agregado se gana entera sobre la mitad que no necesita pronóstico.
        </p>
      </section>

      {/* ---- 4. construct validity ----------------------------------------- */}
      <article className="ficha">
        <div className="ficha__cabeza">
          <h3>¿Mide algo real? · REM20, ocupación de camas</h3>
          <span className="veredicto">pasa en ambas ventanas, por el borde bajo</span>
        </div>
        <div className="ficha__cuerpo">
          <p>
            El objetivo es un percentil de <em>demanda</em>, no de saturación: mide el numerador y
            nunca tuvo el denominador. La pregunta abierta era si una semana sobre el p90 coincide
            con <em>tensión</em> real en el hospital.
          </p>

          <div className="contraste">
            <div className="contraste__lado contraste--antes">
              <h4>Lo que se escribió antes</h4>
              <p>
                Un mes que contiene una semana sobre el p90 del propio servicio se situará sobre la
                norma de ocupación de camas de ese mismo servicio para ese mes del año, por{" "}
                <strong>+0.05 a +0.35 SD</strong>. Las áreas de control — las que una ola
                respiratoria no debería cargar — deben quedar planas. Ventana principal 2022–2026,
                réplica 2015–2019.
              </p>
            </div>
            <div className="contraste__lado contraste--despues">
              <h4>Lo que volvió</h4>
              <p>
                <strong>+0.093 SD</strong> (2022–2026) y <strong>+0.161 SD</strong> (2015–2019),
                controles negativos planos. Pasa — pero el primario cayó en el <em>piso</em> de su
                propio rango, que es un resultado más débil de lo que «se cumplió» deja entender. Al
                día siguiente una auditoría adversarial quitó la componente nacional común — un
                invierno severo levanta alzas y ocupación en todas partes a la vez — y el efecto
                cayó cerca del 40%, a <strong>+0.060</strong> y <strong>+0.092 SD</strong>. Ambos
                intervalos siguen excluyendo el cero. <strong>Esas son las cifras honestas.</strong>
              </p>
            </div>
          </div>

          <p>
            El control estacional era todo: sin él, el mismo contraste da +1.96 pp y +5.24 pp,{" "}
            <strong>entre 4 y 5.6 veces</strong> el efecto deseasonalizado.
          </p>
          <p className="advertencia">
            <b>Cuidado con la traducción a puntos porcentuales.</b> La cifra publicada, «cerca de
            medio punto porcentual de ocupación», corresponde al <strong>+0.093 SD anterior a la
            auditoría</strong>. Sobre la escala auditada nadie la ha recalculado, así que el efecto
            en puntos porcentuales es <em>menor</em> que ese medio punto y no hay un número que
            citar. Lo que sí se sostiene: es pequeño.
          </p>
          <p>
            <strong>La señal es pediátrica.</strong> Medicina, UCI e intermedio pediátricos rinden
            alrededor de +0.19 y +0.21 en ambas épocas; las salas de adultos son un cero preciso en
            la época que se despliega — el área 401, la mejor medida de todo el archivo con unos 103
            servicios, devuelve un intervalo de [−0.059, +0.079]. Esto es{" "}
            <strong>exploratorio replicado, nunca pre-registrado</strong>: salió de abrir una
            comparación agrupada después de verla pasar, y hay que decirlo cada vez — sobre todo
            porque es lo más citable de esta página.
          </p>
          <p className="retirada">
            <b>Retirada:</b> <s>«la señal aparece en medicina y UCI de adultos y pediátricas»</s> —
            publicada el 2026-07-31 y retirada el 2026-08-01. El resultado agrupado no nombraba
            ninguna sala; se escribió la lista de áreas <em>elegidas</em> como si fuera la lista que
            <em> respondió</em>. Alcanzó a propagarse a dos documentos antes de que alguien la
            revisara.
          </p>
          <p>
            Se refutó una objeción por el camino: la ocupación es camas-día ocupadas dividido por
            camas-día <em>disponibles</em>, y las camas cierran cuando el personal toma licencia
            durante una ola, lo que subiría el índice sin un solo paciente más. Las camas-día
            ocupadas suben (+0.119 / +0.132); las disponibles no (+0.033 / −0.000). Son pacientes, no
            camas cerradas, y, en todo caso, el índice subestima el alza por el lado del paciente.
          </p>

          <h4 className="rotulo">Lo que este resultado no autoriza</h4>
          <ul className="limites">
            <li>Una afirmación de magnitud. El efecto es pequeño en cualquiera de sus escalas.</li>
            <li>Una lectura causal. Es una coincidencia medida, no un mecanismo demostrado.</li>
            <li>
              Convertir el efecto mensual en uno semanal. Una semana de alza es una de cada 4.3 del
              mes, así que la cifra medida es una <em>cota inferior</em> — pero cuánto mayor es la
              real no se puede saber desde un archivo mensual. Si alguien cita un porcentaje semanal
              para este producto, se lo inventó.
            </li>
            <li>
              Absolutamente nada sobre los 446 servicios ambulatorios que cargan el 73.7% del
              volumen. No aparecen en ningún informe de camas y son <strong>formalmente no
              verificables</strong> con los datos en disco.
            </li>
          </ul>
        </div>
      </article>

      {/* ---- 5. how to read any figure here -------------------------------- */}
      <section className="pliego__tramo">
        <h3 className="pliego__titulo">Cómo leer cualquier cifra de este proyecto</h3>
        <p>Cinco trampas, todas encontradas midiendo y no razonando.</p>
        <ol className="trampas">
          {TRAMPAS.map(([t, d]) => (
            <li key={t}><b>{t}</b><span>{d}</span></li>
          ))}
        </ol>
      </section>

      {/* ---- 6. the absences ----------------------------------------------- */}
      <section className="pliego__tramo">
        <h3 className="pliego__titulo">Lo que no sabemos</h3>
        <ul className="ausencias">
          <li>
            <b>Tres cuartas partes del volumen no son verificables.</b> Los 446 servicios
            ambulatorios — SAPU, SAR y SUR — cargan el 73.7% de las atenciones respiratorias y no
            tienen denominador de capacidad en ninguna parte de los datos. Entrenan al modelo y no
            reciben alertas, porque en un SAPU una alerta no tiene consecuencia.
          </li>
          <li>
            <b>El objetivo es de todas las edades y la tensión que predice es pediátrica.</b> Si el
            producto debería pronosticar demanda respiratoria <em>pediátrica</em> es una pregunta de
            producto, no de modelado, y está sin responder. Los tramos de edad ya están en el
            cargador de datos, lo que la hace fácil y por eso mismo prematura.
          </li>
          <li>
            <b>Ningún Jefe de Urgencia ha visto esta interfaz.</b> El producto ha tenido exactamente
            una conversación clínica y la interfaz ninguna. Si un ordinal («2ª de 31») es accionable
            para un coordinador o si le resulta inerte es la suposición más riesgosa de todo el
            diseño, y ninguna medición la resuelve.
          </li>
          <li>
            <b>No existe una cifra semanal de tensión hospitalaria.</b> La medición es mensual.
            Convertirla es una suposición, no un resultado.
          </li>
          <li>
            <b>El ajuste es reproducible pero sensible.</b> Permutar el orden de las filas de entrada
            mueve el lift de 2026 a h=1 entre 7.94 y 8.31. Todos los criterios de aceptación
            resisten esa envolvente; una afirmación que descansaba en 0.002 no lo hizo, y se
            corrigió.
          </li>
        </ul>
      </section>
    </section>
  );
}
