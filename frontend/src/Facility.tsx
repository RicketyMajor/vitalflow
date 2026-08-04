/* The facility screen — the whole product. One of the 180 hospital ERs, its season, its alerts and
   what actually happened.

   AC-E1: the calm state is a designed screen. ~40% of these facilities pass a whole season without
   a single alert and for most of them that silence is CORRECT, so this screen must answer "is this
   working?" without the user asking. The ribbon and the vigilance footer are that answer.

   The accent is not used here for the verdict, only where the model actually fired (ribbon cells,
   series columns). A blue headline over "3 alzas, ninguna avisada" would read as a status the ink
   does not mean. */

import type { Facility as F } from "./data";
import { Ribbon } from "./Ribbon";
import { Series } from "./Series";
import { fmt, summarize, verdict } from "./season";

export function Facility({ f }: { f: F }) {
  const summary = summarize(f);
  const { season, watched, alerts, surges, peak } = summary;
  const [titular, glosa] = verdict(summary);

  return (
    <section className="pantalla">
      <article className="tablero">
        <div className="barra">
          <strong>{f.name ?? f.code}{f.comuna ? ` · ${f.comuna}` : ""}</strong>
          <span>{[f.type, f.region, `COD ${f.code}`].filter(Boolean).join(" · ").toUpperCase()}</span>
        </div>

        <div className="estado">
          <p className="estado__rotulo">
            Temporada {f.season} · {watched} de {season} semanas evaluadas
          </p>
          <h2 className="estado__titular">{titular}</h2>
          <p className="estado__glosa">{glosa}</p>
          {/* AC-E7 — the outcome columns exist only because the season is over. */}
          <p className="nota">
            <b>Vista retrospectiva</b> lo ocurrido junto a lo avisado · en operación la semana
            evaluada aún no ha ocurrido y estas columnas van vacías
          </p>
        </div>

        <Ribbon f={f} alerts={alerts} surges={surges} watched={watched} />
        <Series f={f} />

        <dl className="hechos">
          <div className="hecho">
            <dt>Umbral del servicio</dt>
            <dd>{fmt(f.p90)} at/sem</dd>
            <small>
              Percentil 90 de las semanas históricas de este servicio. Es su propia vara, no la de
              otro hospital.
            </small>
          </div>
          <div className="hecho">
            <dt>Avisos emitidos</dt>
            <dd>{alerts}</dd>
            <small>
              A dos semanas desde la última semana cerrada. Es el horizonte que se despliega; el de
              una semana no se muestra porque en operación no existe.
            </small>
          </div>
          <div className="hecho">
            <dt>Semana más alta</dt>
            <dd>{peak === null ? "—" : `Sem ${f.weeks[peak]}`}</dd>
            <small>
              {peak === null
                ? "Este servicio no registra semanas con dato en la temporada."
                : `${f.attentions[peak]} atenciones, el máximo observado de la temporada en este servicio.`}
            </small>
          </div>
        </dl>

        <div className="vigilancia">
          <p><i className="pulso" />Vigilancia activa · <b>{watched}</b> de {season} semanas revisadas</p>
          <p>Temporada {f.season} cerrada · vista retrospectiva</p>
        </div>
      </article>

      <p className="nota"><a href={`#/${f.code}/ahora`}>Ver el pronóstico de esta semana →</a></p>

      <p className="nota nota--pie">
        Esta pantalla muestra una temporada que ya ocurrió, y por eso puede poner el resultado al
        lado del aviso. El producto en operación no puede: la semana evaluada todavía no sucede y
        las columnas de resultado van vacías. La posición que se muestra es un orden dentro de las
        propias semanas de este servicio, nunca una probabilidad — la calibración se midió y se
        rechazó.
      </p>
    </section>
  );
}
