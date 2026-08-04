/* The live operational screen — what the product actually is. This facility, the last closed
   week, and the model's claim about a week that has not happened.

   Everything that separates it from `Facility.tsx` is epistemic, not visual: there is no outcome
   to put beside the alert, so the accent marks a CLAIM, and the ribbon draws the boundary rather
   than captioning it. AC-I7 / AC-I8, `context/specs/alert-interface.md`. */

import type { Live as L } from "./data";
import { Ribbon } from "./Ribbon";
import { Series } from "./Series";
import { CAMPAIGN, claimOf, fmt, freshness, liveState, liveVerdict, ordinal, summarize } from "./season";

export function Live({ f }: { f: L }) {
  const state = liveState(f);
  const claim = claimOf(f);
  const [titular, glosa] = liveVerdict(f, state, claim);
  const { watched, alerts, surges, season } = summarize(f);
  const [anio, semana] = f.origin;
  const aviso = state === "aviso";
  const campana = claim !== null && claim.week >= CAMPAIGN[0] && claim.week <= CAMPAIGN[1];

  return (
    <section className="pantalla">
      <article className="tablero">
        <div className="barra">
          <strong>{f.name ?? f.code}{f.comuna ? ` · ${f.comuna}` : ""}</strong>
          <span>{[f.type, f.region, `COD ${f.code}`].filter(Boolean).join(" · ").toUpperCase()}</span>
        </div>

        <div className={aviso ? "estado estado--alerta" : "estado"}>
          <p className="estado__rotulo">
            {claim ? `Semana ${claim.week} de ${anio}` : `Temporada ${f.season}`}
          </p>
          <h2 className="estado__titular">{titular}</h2>
          <p className="estado__glosa">{glosa}</p>
          {/* AC-I4: both weeks named, the gap DRAWN. No date range — DEIS carries no date column
              and the epidemiological week boundaries cannot be recovered from it. */}
          {claim && (
            <p className="horizonte">
              <em>Semana {semana}</em><i>última cerrada</i>
              <span className="tramo" />
              <em>Semana {claim.week}</em><i>evaluada</i>
            </p>
          )}
        </div>

        <Ribbon f={f} alerts={alerts} surges={surges} watched={watched}
                now={semana}
                claim={claim ? { week: claim.week, alert: !!claim.alert, live: state !== "vencido" }
                             : undefined} />
        <Series f={f} />

        <dl className="hechos">
          <div className="hecho">
            <dt>Posición de la semana</dt>
            <dd>{claim ? `${ordinal(claim.rank)} de ${claim.of}` : "—"}</dd>
            <small>
              {claim
                ? "Entre las semanas de esta temporada, ordenadas por demanda esperada en este servicio. Es un orden, nunca una probabilidad."
                : "Sin pronóstico para esta semana, este servicio no tiene posición que mostrar."}
            </small>
          </div>
          <div className="hecho">
            <dt>Umbral del servicio</dt>
            <dd>{fmt(f.p90)} at/sem</dd>
            <small>
              Percentil 90 de las semanas históricas de este servicio. Es su propia vara, no la de
              otro hospital.
            </small>
          </div>
          <div className="hecho">
            <dt>Presupuesto</dt>
            {/* Without a claim there is no week to place inside or outside the campaign, and
                "Fuera de campaña" would be a false statement about the calendar — weeks 29 and 31
                both sit inside 22–35. The cell goes silent for the same reason the position does. */}
            <dd>{!claim ? "—" : campana ? "Campaña abierta" : "Fuera de campaña"}</dd>
            <small>
              {!claim
                ? "Sin semana pronosticada no hay período presupuestario que evaluar."
                : campana
                  ? `La semana ${claim.week} cae dentro de la Campaña de Invierno decretada: el turno extra se puede pagar.`
                  : `La semana ${claim.week} queda fuera de las semanas ${CAMPAIGN[0]}–${CAMPAIGN[1]}: el servicio opera con la dotación aprobada el mes anterior.`}
            </small>
          </div>
        </dl>

        {/* AC-I5 — only on the alert variant: levers a coordinator cannot use are noise on a
            screen whose primary state is calm. */}
        {aviso && (
          <div className="palancas">
            <h3>Qué se puede mover a tiempo</h3>
            <ol>
              <li><b>01</b><span>Activar el plan de contingencia de camas.</span></li>
              <li><b>02</b><span>Reasignar funciones internas del servicio.</span></li>
              <li><b>03</b><span>Autorizar turnos espejo <i>— con cargo al presupuesto de campaña</i>.</span></li>
            </ol>
            <p className="descartada">
              <b>La dotación base no está en esta lista, y no es un olvido.</b> El rol mensual
              cierra entre el 20 y el 25 del mes anterior, así que la contratación de refuerzo
              necesita entre 4 y 7 semanas de aviso. Este aviso llega con 2. Los calendarios no se
              cruzan y ningún modelo lo arregla.
            </p>
          </div>
        )}

        <div className="vigilancia">
          <p><i className="pulso" />Vigilancia activa · <b>{watched}</b> de {season} semanas revisadas</p>
          <p>
            Fuente DEIS hasta la semana {semana} de {anio} ·{" "}
            {freshness(f.stamp).dias === 0 ? "actualizado hoy" : `actualizado hace ${freshness(f.stamp).dias} días`}
          </p>
        </div>
      </article>

      <p className="nota">
        <a href={`#/${f.code}`}>
          Ver la temporada {f.season - 1} cerrada, con lo ocurrido al lado de lo avisado →
        </a>
      </p>

      <p className="nota nota--pie">
        Esta pantalla afirma algo sobre una semana que todavía no ocurre: no hay resultado que poner
        al lado del aviso, y por eso la celda pronosticada va delineada y no rellena. La posición es
        un orden dentro de las propias semanas de este servicio, nunca una probabilidad — la
        calibración se midió y se rechazó. <b>Ninguna persona de las que trabajan en una urgencia
        hospitalaria ha leído esta interfaz todavía.</b>
      </p>
    </section>
  );
}
