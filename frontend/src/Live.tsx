import type { Live as L } from "./data";

export function Live({ f }: { f: L }) {
  return <pre className="nota">{JSON.stringify(f.forecast, null, 2)} · origen {f.origin.join(" w")}</pre>;
}
