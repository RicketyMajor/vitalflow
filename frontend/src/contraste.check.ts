/* AC-F1 / AC-F2 — el contraste de los tokens, medido, en los dos temas.
 *
 *  Este chequeo LEE `styles.css`. No lleva su propia copia de los valores, a propósito: una copia
 *  es exactamente la deriva que el ítem G existe para prevenir, movida de lugar. Si alguien cambia
 *  un token, esto lo mide contra el archivo cambiado o no mide nada.
 *
 *  Y existe como archivo del repo por una razón concreta: el detector mecánico que dos artefactos
 *  del proyecto citan como evidencia (`detect.mjs --json -> []`) vive FUERA del repositorio, en una
 *  skill. Un chequeo que un clon no puede correr no es un chequeo que el proyecto tenga.
 *
 *  Umbrales WCAG 2.2: 4.5:1 texto normal (1.4.3) · 3:1 texto grande y componentes/graficos con
 *  significado (1.4.11). Un divisor decorativo NO cae bajo 1.4.11 y no se afirma aca. */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const CSS = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "styles.css"), "utf8");

/** Las declaraciones `--token: valor` de un bloque, ubicado por su selector literal. */
function bloque(selector: string): Record<string, string> {
  const i = CSS.indexOf(selector);
  if (i < 0) throw new Error(`contraste.check: no existe el bloque \`${selector}\` en styles.css`);
  const abre = CSS.indexOf("{", i);
  // los bloques de tema son planos (sin anidamiento), asi que la primera llave de cierre alcanza
  const cuerpo = CSS.slice(abre + 1, CSS.indexOf("}", abre));
  const out: Record<string, string> = {};
  for (const m of cuerpo.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) out[m[1]] = m[2].trim();
  return out;
}

type RGB = [number, number, number];

function hex(h: string): RGB {
  let s = h.replace("#", "").trim();
  if (s.length === 3) s = [...s].map((c) => c + c).join("");
  return [0, 2, 4].map((i) => parseInt(s.slice(i, i + 2), 16) / 255) as RGB;
}

/** Compone un color (opaco o rgba) sobre un fondo ya opaco. */
function sobre(valor: string, fondo: RGB): RGB {
  if (valor.startsWith("#")) return hex(valor);
  const m = valor.match(/rgba?\(([^)]+)\)/);
  if (!m) throw new Error(`contraste.check: no se pudo leer el color \`${valor}\``);
  const p = m[1].split(",").map((x) => Number(x.trim()));
  const [r, g, b] = [p[0] / 255, p[1] / 255, p[2] / 255];
  const a = p[3] ?? 1;
  return [r, g, b].map((c, i) => c * a + fondo[i] * (1 - a)) as RGB;
}

const lin = (c: number) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const L = (c: RGB) => 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
const ratio = (a: RGB, b: RGB) => {
  const [hi, lo] = [L(a), L(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

/* [primer plano, fondo, minimo, donde se usa]
   Solo pares que EXISTEN en el CSS; cada uso se verifico por grep antes de entrar a esta lista. */
const PARES: [string, string, number, string][] = [
  ["--tinta", "--muro", 4.5, "cuerpo sobre el muro"],
  ["--tinta", "--pizarra", 4.5, "cuerpo sobre el tablero"],
  ["--rotulo", "--muro", 4.5, "parrafos secundarios (.que__entrada, .pais__lectura p)"],
  ["--rotulo", "--pizarra", 4.5, "rotulos sobre el tablero (.salida span, .barra)"],
  ["--tenue", "--muro", 4.5, ".nota, .que__palancas span, .pais__eje"],
  ["--tenue", "--pizarra", 4.5, ".cinta__titulo, .cinta__eje, .leyenda, .columna em/span"],
  ["--alerta", "--muro", 4.5, "el acento sobre el muro (.acceso__via--fuerte b)"],
  ["--alerta", "--pizarra", 4.5, "el acento sobre el tablero (.salida--fuerte b, .despliega:hover)"],
];

/* Graficos CON SIGNIFICADO — 1.4.11 aplica. Un divisor decorativo no esta aca. */
const GRAFICOS: [string, string, number, string][] = [
  ["--alerta", "--hueco", 3.0, "semana alertada contra su propio pozo"],
  ["--tinta", "--pizarra", 3.0, "semana con alza (.semana--alza) sobre el tablero"],
];

/** Los tres escalones de gris deben seguir distinguiendose ENTRE SI. AC-F2.
    Sin esto, la forma mas barata de pasar AC-F1 es colapsar la rampa en dos grises. */
const RAMPA: [string, string, number][] = [
  ["--tinta", "--rotulo", 1.3],
  ["--rotulo", "--tenue", 1.3],
];

/** Dos significados distintos no pueden dibujarse igual. La celda por defecto de la cinta es
    «nadie reporto esta semana» (regla 34) y `.semana--revisada` es «se observo y no hubo alza».
    En plano median 1.03:1 en claro — el mismo gris para dos cosas distintas.
    El canal que los separa puede ser LUMINANCIA o GEOMETRIA, y el CSS eligio geometria: un rayado,
    porque subir el brillo del pozo lo volveria ruidoso en 832 celdas (la misma decision de AC-E4).
    Asi que esto NO se afirma como contraste: se afirma que existe ALGUN canal. */
const ABSENCIA: [string, string, string][] = [
  [".semana {", ".semana--revisada {", "celda: sin dato vs revisada"],
  [".llave {", ".llave--revisada {", "leyenda: la llave de sin dato vs la de revisada"],
];

/** El valor de `background` declarado en un selector literal. */
function fondoDe(selector: string): string {
  const i = CSS.indexOf(selector);
  if (i < 0) throw new Error(`contraste.check: no existe \`${selector}\` en styles.css`);
  const cuerpo = CSS.slice(CSS.indexOf("{", i) + 1, CSS.indexOf("}", CSS.indexOf("{", i)));
  const m = cuerpo.match(/background\s*:\s*([^;]+);/);
  return m ? m[1].trim() : "";
}

const TEMAS: [string, string[]][] = [
  ["claro", [":root {", ':root[data-theme="light"]']],
  ["oscuro", [":root {", "@media (prefers-color-scheme: dark)", ':root[data-theme="dark"]']],
];

let fallas = 0;
const linea = (ok: boolean, r: number, min: number, txt: string) => {
  if (!ok) fallas++;
  console.log(`  ${ok ? "OK   " : "FALLA"} ${r.toFixed(2).padStart(5)} (min ${min})  ${txt}`);
};

for (const [nombre, selectores] of TEMAS) {
  // base :root, luego cada bloque del tema encima
  let T: Record<string, string> = {};
  for (const s of selectores) {
    if (s.startsWith("@media")) {
      // el :root anidado dentro del @media
      const i = CSS.indexOf(s);
      const j = CSS.indexOf(":root", i);
      T = { ...T, ...bloque(CSS.slice(j, j + 6)) };
      const abre = CSS.indexOf("{", j);
      const cuerpo = CSS.slice(abre + 1, CSS.indexOf("}", abre));
      for (const m of cuerpo.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) T[m[1]] = m[2].trim();
    } else {
      T = { ...T, ...bloque(s) };
    }
  }
  const muro = sobre(T["--muro"], [1, 1, 1]);
  const res = (k: string, fondo: RGB) => sobre(T[k], fondo);

  console.log(`\n=== ${nombre} ===`);
  for (const [fg, bg, min, uso] of PARES) {
    const fondo = res(bg, muro);
    const r = ratio(res(fg, fondo), fondo);
    linea(r >= min, r, min, `${fg} / ${bg} — ${uso}`);
  }
  console.log(`  --- graficos con significado (1.4.11) ---`);
  for (const [fg, bg, min, uso] of GRAFICOS) {
    const fondo = res(bg, muro);
    const r = ratio(res(fg, fondo), fondo);
    linea(r >= min, r, min, `${fg} / ${bg} — ${uso}`);
  }
  console.log(`  --- la rampa sigue siendo tres escalones (AC-F2) ---`);
  for (const [a, b, min] of RAMPA) {
    const pz = res("--pizarra", muro);
    const r = ratio(res(a, pz), res(b, pz));
    linea(r >= min, r, min, `${a} vs ${b} — separacion entre escalones`);
  }
}

/* --- la ausencia se distingue por ALGUN canal (no depende del tema) --------------------------- */
console.log(`\n=== la ausencia tiene su propio canal ===`);
for (const [selA, selB, uso] of ABSENCIA) {
  const a = fondoDe(selA), b = fondoDe(selB);
  const geometria = /gradient|--rayado/.test(a) && !/gradient|--rayado/.test(b);
  if (!geometria) {
    fallas++;
    console.log(`  FALLA  ${uso}`);
    console.log(`         \`${selA}\` -> ${a || "(sin background)"}`);
    console.log(`         \`${selB}\` -> ${b || "(sin background)"}`);
    console.log(`         Los dos estados se pintan con el mismo canal. En claro --hueco vs --borde`);
    console.log(`         mide 1.03:1, asi que sin geometria son el mismo gris.`);
  } else {
    console.log(`  OK     ${uso} — canal: geometria (${a.match(/--rayado|gradient/)![0]})`);
  }
}

if (fallas) {
  console.error(`\ncontraste.check: ${fallas} par(es) bajo su umbral.`);
  process.exit(1);
}
console.log("\ncontraste.check: OK");
