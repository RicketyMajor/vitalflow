/* AC-E4 — the weekly series against the facility's own p90, with alerted weeks and observed surge
   weeks both marked so agreement AND disagreement read without a legend lookup.

   There is exactly one accent in this product (institutional blue) and triage colours are banned,
   so colour cannot separate "we warned" from "it happened". Geometry does:

     blue column    = the model warned (h=2, the horizon that deploys)
     above the rule = it actually happened

   Agreement is a dot standing on a blue column · a false alarm is a blue column with nothing above
   the rule · a MISS is a dot above the rule with no blue under it. Facility 129103 is the test
   case: surges in weeks 19/21/33, its only alert in week 50.

   **The x axis is the epidemiological week, never the array position.** Five facilities are scored
   on fewer than 52 weeks and their weeks are NOT contiguous — 105107 has 37 of them scattered
   between week 1 and week 49. Drawing those adjacent would compress twelve missing weeks into
   nothing and misstate when a surge happened. Every facility is plotted on the same 1..52 axis and
   a gap breaks the line.

   h=1 is deliberately not plotted. Serving origin is W-1, so h=1 is a horizon the deployment does
   not have; drawing it invites quoting it. */

import { useState } from "react";
import type { Facility } from "./data";
import { CAMPAIGN, axisWeeks, byWeek, fmt, runs, seasonLength, summarize } from "./season";

const W = 800;
const H = 150;              // plot height
const PAD_L = 8;
const PAD_R = 46;           // room for the p90 label
const TOP = 12;
const LANE = 22;            // the h=2 alert lane, below the axis
const BOTTOM = 16;

export function Series({ f }: { f: Facility }) {
  const [hover, setHover] = useState<number | null>(null);

  const last = seasonLength(f.weeks);
  const step = (W - PAD_L - PAD_R) / (last - 1);
  const x = (w: number) => PAD_L + (w - 1) * step;
  const at = byWeek(f.weeks);
  const value = (w: number) => {
    const i = at.get(w);
    return i === undefined ? null : f.attentions[i];
  };
  const flag = (a: number[], w: number) => {
    const i = at.get(w);
    return i === undefined ? 0 : a[i];
  };

  const seen = f.attentions.filter((v): v is number => v !== null);
  const top = Math.max(f.p90, ...(seen.length ? seen : [f.p90])) * 1.08 || 1;
  const y = (v: number) => TOP + H - (v / top) * H;

  const all = Array.from({ length: last }, (_, i) => i + 1);
  const paths = runs(f.weeks, f.attentions, last).map((weeks) =>
    weeks.map((w, k) => `${k ? "L" : "M"}${x(w).toFixed(1)},${y(value(w)!).toFixed(1)}`).join(" "));

  const { alerts, surges, caught } = summarize(f);
  const height = TOP + H + LANE + BOTTOM;

  return (
    <section className="serie">
      <p className="cinta__titulo">
        <span>Atenciones por semana · umbral del servicio</span>
        <span>{surges} sobre el umbral · {alerts} con aviso · {caught} coinciden</span>
      </p>

      <svg
        viewBox={`0 0 ${W} ${height}`}
        role="img"
        onMouseLeave={() => setHover(null)}
        aria-label={
          `Atenciones respiratorias semanales de ${f.name ?? f.code} en ${f.season}, contra su ` +
          `propio percentil 90 de ${fmt(f.p90)} atenciones. ${surges} semanas quedaron sobre el ` +
          `umbral y el modelo emitió ${alerts} avisos a dos semanas; ${caught} coinciden.`
        }
      >
        <rect x={x(CAMPAIGN[0]) - step / 2} y={TOP} width={(CAMPAIGN[1] - CAMPAIGN[0] + 1) * step}
              height={H} fill="var(--campana)" />
        {/* labelled, because an unlabelled wash beside a blue column reads as a second alert */}
        <text x={x(CAMPAIGN[0]) + 4} y={TOP + 9}>CAMPAÑA DE INVIERNO</text>

        {/* the model spoke: one column per alerted week */}
        {all.map((w) => flag(f.h2.alert, w) === 1 && (
          <rect key={`a${w}`} x={x(w) - step / 2} y={TOP} width={step} height={H}
                fill="var(--alerta-df)" />
        ))}

        {hover !== null && (
          <line x1={x(hover)} x2={x(hover)} y1={TOP} y2={TOP + H} stroke="var(--borde)" />
        )}

        {/* the facility's own p90 — its own yardstick, not another hospital's */}
        <line x1={PAD_L - 4} x2={W - PAD_R} y1={y(f.p90)} y2={y(f.p90)} stroke="var(--tenue)" />
        <text x={W - PAD_R + 6} y={y(f.p90) + 3.5}>p90 {fmt(f.p90)}</text>

        {paths.map((d, i) => (
          <path key={`p${i}`} d={d} fill="none" stroke="var(--rotulo)" strokeWidth={2}
                strokeLinejoin="round" strokeLinecap="round" />
        ))}

        {/* it happened: only weeks over the rule carry a dot, so the mark confirms the geometry */}
        {all.map((w) => {
          const v = value(w);
          return flag(f.surge, w) === 1 && v !== null && (
            <circle key={`s${w}`} cx={x(w)} cy={y(v)} r={3.5} fill="var(--tinta)"
                    stroke="var(--pizarra)" strokeWidth={2} />
          );
        })}

        <line x1={PAD_L - 4} x2={W - PAD_R} y1={TOP + H} y2={TOP + H} stroke="var(--borde-int)" />
        {all.map((w) => flag(f.h2.alert, w) === 1 && (
          <rect key={`t${w}`} x={x(w) - 1.5} y={TOP + H + 6} width={3} height={7}
                fill="var(--alerta)" />
        ))}
        <text x={PAD_L - 4} y={TOP + H + 12.5} fill="var(--alerta)">AVISO h=2</text>

        {axisWeeks(last).map((w) => (
          <text key={`x${w}`} x={x(w)} y={height - 2} textAnchor="middle">SEM {w}</text>
        ))}

        {/* hit targets: full plot height, one per week, so a 15px column is easy to hover */}
        {all.map((w) => (
          <rect key={`h${w}`} x={x(w) - step / 2} y={TOP} width={step} height={H + LANE}
                fill="transparent" tabIndex={0} role="button" aria-label={`Semana ${w}`}
                onMouseEnter={() => setHover(w)} onFocus={() => setHover(w)} />
        ))}
      </svg>

      <p className="serie__lectura" aria-live="polite">
        {hover === null ? (
          <>
            <span>Columna azul = el modelo avisó, 2 semanas antes</span>
            <span>Punto sobre la línea = el alza ocurrió</span>
            <span>Punto sin columna = nadie fue avisado</span>
          </>
        ) : at.get(hover) === undefined ? (
          <>
            <span>SEM {hover}</span>
            <b>sin dato</b>
            <span>esta semana no fue evaluada en este servicio</span>
          </>
        ) : (
          <>
            <span>SEM {hover}</span>
            <b>{value(hover)} at</b>
            <span>{flag(f.surge, hover) ? "sobre el umbral" : "dentro del rango"}</span>
            {flag(f.h2.alert, hover) ? <i>con aviso</i> : <span>sin aviso</span>}
            <span>{flag(f.h2.rank, hover)}ª de {f.weeks.length} por demanda esperada</span>
          </>
        )}
      </p>

      <details className="tabla">
        <summary>Ver la temporada semana a semana</summary>
        <table>
          <thead>
            <tr><th>Sem</th><th>Atenciones</th><th>Sobre umbral</th><th>Aviso h=2</th><th>Posición</th></tr>
          </thead>
          <tbody>
            {f.weeks.map((w, i) => (
              <tr key={w}>
                <td>{w}</td>
                <td>{f.attentions[i] ?? "—"}</td>
                <td>{f.surge[i] ? "sí" : ""}</td>
                <td>{f.h2.alert[i] ? "sí" : ""}</td>
                <td>{f.h2.rank[i] || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </section>
  );
}
