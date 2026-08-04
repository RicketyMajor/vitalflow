/* Everything about a season that is arithmetic rather than rendering, so it can be checked without
   a browser: `npm run check`. The week-indexing here is the part that had a real bug — five
   facilities are scored on non-contiguous weeks, and indexing by array position drew twelve missing
   weeks as none at all. */

import type { Claim, Facility, Live } from "./data";

export const CAMPAIGN: [number, number] = [22, 35];   // Campaña de Invierno, as declared

/** DEIS publishes weekly, so one missed refresh is visible on the ninth day. */
export const DIAS_FRESCO = 8;

/** AC-I9. How old the served export is, and whether that is old enough to say so out loud.
 *  A future stamp is a clock disagreement, never freshness — clamped at 0 rather than negative. */
export function freshness(stamp: string, today = new Date()) {
  const dias = Math.max(0, Math.floor(
    (today.getTime() - Date.parse(`${stamp}T00:00:00`)) / 86_400_000));
  return { dias, viejo: dias > DIAS_FRESCO };
}

/** The season's full width in weeks: 52, or more if the year carries a week 53. */
export const seasonLength = (weeks: number[]) => Math.max(52, ...weeks);

/** Sparse axis: quarters of the season plus its last week. */
export const axisWeeks = (last: number) => [...new Set([1, 13, 26, 39, last])];

/** Two significant figures on screen; the p90 arrives rounded to one decimal. */
export const fmt = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1));

/** Week -> row index. Absent weeks are absent, not zero. */
export const byWeek = (weeks: number[]) => new Map(weeks.map((w, i) => [w, i]));

/** Runs of consecutive OBSERVED weeks, in week space. A gap breaks the line instead of being
 *  interpolated across — a straight segment over twelve missing weeks is a claim nobody measured. */
export function runs(weeks: number[], attentions: (number | null)[], last: number): number[][] {
  const at = byWeek(weeks);
  const out: number[][] = [];
  let cur: number[] = [];
  for (let w = 1; w <= last; w++) {
    const i = at.get(w);
    if (i === undefined || attentions[i] === null) {
      if (cur.length > 1) out.push(cur);
      cur = [];
      continue;
    }
    cur.push(w);
  }
  if (cur.length > 1) out.push(cur);
  return out;
}

export type Summary = {
  season: number; watched: number; alerts: number; surges: number; caught: number;
  peak: number | null;
};

export function summarize(f: Facility): Summary {
  return {
    season: seasonLength(f.weeks),
    watched: f.attentions.filter((v) => v !== null).length,
    alerts: f.h2.alert.reduce((s, a) => s + a, 0),
    surges: f.surge.reduce((s, v) => s + v, 0),
    // agreement at the horizon that deploys: the model said week w, and week w was over the p90
    caught: f.surge.reduce((s, v, i) => s + (v && f.h2.alert[i] ? 1 : 0), 0),
    peak: f.attentions.reduce(
      (best, v, i) => (v !== null && (best === null || v > f.attentions[best]!) ? i : best),
      null as number | null,
    ),
  };
}

/* ---- the live screen: a claim about a week that has not happened ------------------------- */

/** «la semana» is feminine: 2ª, never 2°. */
export const ordinal = (n: number) => `${n}ª`;

/** Only h=2 reaches the screen. h=1 targets the week that is still settling — a horizon the
 *  deployment does not have (2026-07-28) — and it stays in the file, off screen, exactly as the
 *  explorer keeps it. */
export const claimOf = (f: Live, horizon = 2): Claim | null =>
  f.forecast.find((c) => c.horizon === horizon) ?? null;

export type LiveState = "vencido" | "sin-dato" | "aviso" | "calma";

/** The live screen's state, in precedence order.
 *
 *  `vencido` OUTRANKS everything, including an alert: a forecast whose export is older than one
 *  DEIS publication cycle is a claim about a week that has probably already happened, and
 *  rendering it as current is the same lie as a live screen with no refresh job behind it. */
export function liveState(f: Live, today = new Date()): LiveState {
  if (freshness(f.stamp, today).viejo) return "vencido";
  const c = claimOf(f);
  if (!c) return "sin-dato";
  return c.alert ? "aviso" : "calma";
}

/** Headline and gloss. `sin-dato` must never read as calm — the calm screen says "watched,
 *  nothing found", and here nobody watched. */
export function liveVerdict(f: Live, state: LiveState, c: Claim | null): [string, string] {
  const [, semana] = f.origin;
  if (state === "vencido") {
    const { dias } = freshness(f.stamp);
    return ["Pronóstico vencido",
      `El último pronóstico publicado apunta a la semana ${c ? c.week : semana + 2} y se generó ` +
      `hace ${dias} días. El refresco semanal no se ha ejecutado, así que esta pantalla no ` +
      `afirma nada sobre la semana en curso.`];
  }
  if (state === "sin-dato")
    return ["Sin pronóstico esta semana",
      `Este servicio no reportó la semana ${semana} o alguna de las anteriores que el modelo ` +
      `necesita, así que no hay nada que pronosticar. No es una temporada en calma: es una ` +
      `semana que nadie observó.`];
  if (state === "calma")
    return ["Sin aviso",
      `La semana ${c!.week} no aparece entre las de mayor demanda esperada para este servicio. ` +
      `Es el estado más frecuente del sistema: 94% de las semanas-servicio no llevan aviso.`];
  return ["Alza probable",
    `La semana ${c!.week} quedaría entre las de mayor demanda esperada para este servicio, por ` +
    `encima de su propio umbral histórico.`];
}

/** The retrospective verdict. Deliberately unaccented: the institutional ink means "the model
 *  spoke", and painting a headline with it would turn it into a quality signal it does not carry. */
export function verdict({ watched, alerts, surges, caught }: Summary): [string, string] {
  if (surges === 0 && alerts === 0)
    return ["Temporada en calma",
      `${watched} semanas revisadas y ninguna superó el umbral de este servicio. El modelo no ` +
      `emitió avisos, y no tenía por qué: no hubo nada que avisar. Es el estado más frecuente ` +
      `del sistema, no una pantalla vacía.`];
  if (surges === 0)
    return [`${alerts} ${alerts === 1 ? "aviso" : "avisos"} · ningún alza`,
      `El modelo señaló ${alerts === 1 ? "una semana" : `${alerts} semanas`} que después ` +
      `quedaron dentro del rango habitual del servicio.`];
  if (caught === 0)
    return [`${surges} ${surges === 1 ? "alza" : "alzas"} · ninguna avisada`,
      `Las semanas sobre el umbral de este servicio no fueron anticipadas con dos semanas de ` +
      `anticipación. Es la falla que esta vista existe para mostrar.`];
  return [`${caught} de ${surges} alzas avisadas`,
    `Semanas sobre el umbral de este servicio que el modelo señaló con dos semanas de ` +
    `anticipación. Las demás quedaron sin aviso.`];
}
