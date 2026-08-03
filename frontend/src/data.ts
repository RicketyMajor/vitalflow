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

export type Index = { season: number; retrospective: boolean; facilities: IndexRow[] };

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

export const loadIndex = () => load<Index>("data/facilities.json");
export const loadFacility = (code: string) => load<Facility>(`data/facility/${code}.json`);
