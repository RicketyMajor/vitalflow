/* The shape written by `src/models/export_frontend.py`. Two things it deliberately does NOT carry:
   `score` (calibration was measured and rejected, so a probability would be dishonest — AC-E2) and
   any per-week array in the index (first paint must not pull 180 files — AC-E6). */

export type Horizon = { alert: number[]; rank: number[] };

export type Meta = {
  code: string;
  name: string | null;
  comuna: string | null;
  region: string | null;
  type: string | null;
  complexity: string | null;
};

export type IndexRow = Meta & { weeks: number; alerts: number; surges: number };

export type Index = {
  season: number;
  retrospective: boolean;
  /** AC-I9, written by `release_stamp`. `settled_through` is read off the exported panel so it
      cannot claim to be fresher than the data; `stamp` is when the export ran and is what ages if
      the weekly refresh job stops; `published` is DEIS's own date, absent unless `refresh.py` ran. */
  stamp: string;
  settled_through: [number, number];
  published: string | null;
  facilities: IndexRow[];
};

export type Facility = Meta & {
  season: number;
  /** The outcome arrays exist only because the season is over. Blank in live use — AC-E7. */
  retrospective: boolean;
  p90: number;
  weeks: number[];
  attentions: (number | null)[];
  surge: number[];
  onset: number[];
  h1: Horizon;
  h2: Horizon;
};

const base = import.meta.env.BASE_URL;
const cache = new Map<string, Promise<unknown>>();

function load<T>(path: string): Promise<T> {
  let hit = cache.get(path);
  if (!hit) {
    hit = fetch(base + path).then((r) => {
      if (!r.ok) throw new Error(`${path}: ${r.status}`);
      return r.json();
    });
    cache.set(path, hit);
  }
  return hit as Promise<T>;
}

/** What the model claims about a week nobody has seen. `rank` of `of` is the ONLY quantity the
    interface may show about it — a probability was measured and rejected (AC-I2). */
export type Claim = { horizon: number; week: number; alert: number; rank: number; of: number };

export type Live = Facility & {
  /** The last settled week the claim was computed from: `[year, week]`. */
  origin: [number, number];
  /** When the export ran. The claim dates itself: a forecast whose origin is weeks old is a
      statement about a week that has already happened, and the screen must refuse it. */
  stamp: string;
  forecast: Claim[];
};

/** The season as the country saw it, written by `export_frontend.build_nacional`. The portada reads
    every figure it states from here — including the ones it derives, like how tightly the regions
    move together — so no number on that surface can drift away from the model that produced it.
    Series are RAW weekly totals: the Metropolitana has 24 hospital ERs and Arica has one, so the
    page normalises each region against its own peak week. Dividing here would have thrown that
    away for every other reader. */
export type Region = { nombre: string; servicios: number; serie: (number | null)[] };

/** Backlog item G, class A: the figures the WEEKLY refresh moves, in CI, with nobody watching.
    `#/metodo` and `#/evidencia` stated these in prose and had already drifted — the pages said 446
    ambulatory facilities carrying 73.7% of attentions when the panel held 448 carrying 72.6%, and
    named no window for the percentage. Read at render time there is nothing left to desynchronise.

    The three counts EXHAUST the panel, and `otros` is why: 180 + 448 is 628, not 632. Four
    facilities are neither (two `Urgencia Especializada`, two with no type at all). The old
    two-segment bar folded them into the alerted side to make the widths close. */
export type Cobertura = {
  panel: number;
  ueh: number;
  ambulatorios: number;
  otros: number;
  /** Percent of respiratory attentions, over the whole panel — `anios`, COVID years excluded. */
  share_ambulatorio: number;
  share_ueh: number;
  anios: [number, number];
};

export type Nacional = {
  season: number;
  stamp: string;
  settled_through: [number, number];
  published: string | null;
  semanas: number[];
  nacional: (number | null)[];
  /** North to south, ordered by the smallest DEIS facility code in each region. */
  regiones: Region[];
  servicios: number;
  alertas: number;
  alzas: number;
  cobertura: Cobertura;
};

export const loadIndex = () => load<Index>("data/facilities.json");
export const loadNacional = () => load<Nacional>("data/nacional.json");
export const loadFacility = (code: string) => load<Facility>(`data/facility/${code}.json`);
export const loadLive = (code: string) => load<Live>(`data/live/${code}.json`);
