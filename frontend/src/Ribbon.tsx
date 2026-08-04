/** The signature: the season as a strip, so silence reads as accumulated surveillance.
 *
 *  One cell per epidemiological week of the whole season, not one per scored row — five facilities
 *  are scored on non-contiguous weeks and packing those together would draw a short season as a
 *  full one. A week with no row is a `sin dato` well, which is the honest rendering and the one
 *  that makes "37 de 52 revisadas" legible.
 *
 *  Shared by the retrospective screen and the live one. **With `now` and `claim` omitted it renders
 *  exactly as it did when it lived in `Facility.tsx`** — that is what keeps the explorer honest
 *  while the live screen adds a boundary to it. */

import type { Facility as F } from "./data";
import { CAMPAIGN, axisWeeks, byWeek, seasonLength } from "./season";

export function Ribbon({ f, alerts, surges, watched, now, claim }: {
  f: F; alerts: number; surges: number; watched: number;
  /** The last settled week. Everything to its left happened. Omitted on the retrospective screen,
      where every week in the file happened by definition. */
  now?: number;
  /** The claimed week, and whether it is claimed as an alert. `live` false when the forecast has
      expired: the cell still marks the week, but not in the ink that means "the model spoke". */
  claim?: { week: number; alert: boolean; live: boolean };
}) {
  const last = seasonLength(f.weeks);
  const at = byWeek(f.weeks);
  const gaps = last - f.weeks.length;
  return (
    <div className="cinta">
      <p className="cinta__titulo">
        <span>Temporada {f.season} · semana a semana</span>
        <span>{watched} de {last} revisadas · {surges} con alza · {alerts} con aviso</span>
      </p>
      <div className="cinta__pista" role="img"
           aria-label={`Cinta de las ${last} semanas de ${f.season}: ${watched} revisadas, ` +
                       `${surges} sobre el umbral del servicio y ${alerts} con aviso a dos semanas.`}>
        {Array.from({ length: last }, (_, k) => k + 1).map((w) => {
          const i = at.get(w);
          return (
            <div key={w} className={[
              "semana",
              i !== undefined && f.attentions[i] !== null ? "semana--revisada" : "",
              i !== undefined && f.surge[i] ? "semana--alza" : "",
              i !== undefined && f.h2.alert[i] ? "semana--alertada" : "",
              w >= CAMPAIGN[0] && w <= CAMPAIGN[1] ? "semana--campana" : "",
              now === w ? "semana--ahora" : "",
              claim?.week === w
                ? (claim.alert && claim.live ? "semana--objetivo" : "semana--objetivo-calma")
                : "",
            ].filter(Boolean).join(" ")} />
          );
        })}
      </div>
      <p className="cinta__eje">
        {axisWeeks(last).map((w) => <span key={w}>SEM {w}</span>)}
      </p>
      <p className="leyenda">
        <span><i className="llave llave--revisada" />revisada, sin alza</span>
        <span><i className="llave llave--alza" />sobre el umbral</span>
        <span><i className="llave llave--alertada" />con aviso</span>
        {gaps > 0 && <span><i className="llave" />sin dato ({gaps})</span>}
        <span><i className="llave llave--campana" />campaña de invierno</span>
        {claim && <span><i className={claim.alert && claim.live
          ? "llave llave--objetivo" : "llave llave--objetivo-calma"} />semana pronosticada</span>}
      </p>
    </div>
  );
}
