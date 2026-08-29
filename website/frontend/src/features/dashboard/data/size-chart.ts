/**
 * Size-chart intake: parsing, validation and provenance.
 *
 * Every sizing "source" in the prototype called one function that invented
 * `80 + 4n` for every field of every size and stamped it with whichever source
 * the merchant happened to click. A garment could reach QA carrying numbers no
 * one had ever measured, which is the single most dangerous thing this product
 * can do — a wrong measurement is a returned parcel and a lost customer.
 *
 * Nothing here fabricates a value. A chart exists only if a person typed it or
 * a file contained it, and it is only "complete" once every required field of
 * every Shopify size holds a plausible number in a known unit.
 */
import { MEASUREMENT_FIELDS } from "./ingestion";
import type { GarmentCategory, SizeRow } from "./types";

export type Unit = "cm" | "in";

export const UNIT_LABELS: Record<Unit, string> = { cm: "Centimetres", in: "Inches" };

/** Everything is stored in centimetres; the merchant may work in either. */
export function toCm(value: number, unit: Unit): number {
  return unit === "in" ? Math.round(value * 2.54 * 10) / 10 : value;
}

export function fromCm(valueCm: number, unit: Unit): number {
  return unit === "in" ? Math.round((valueCm / 2.54) * 10) / 10 : valueCm;
}

/**
 * Plausible ranges in centimetres, per measurement key.
 *
 * These are wide on purpose — the job is catching a decimal point in the wrong
 * place or inches typed into a centimetre column, not second-guessing a
 * designer.
 */
const RANGE_CM: Record<string, [number, number]> = {
  bust: [50, 200], chest: [50, 200], waist: [40, 200], hip: [50, 220],
  shoulder: [20, 80], length: [15, 220], sleeve: [10, 100], armhole: [10, 70],
  rise: [15, 60], inseam: [10, 110], outseam: [20, 150], thigh: [20, 100],
  legOpening: [8, 80], hem: [20, 200], width: [5, 300],
};

export interface FieldIssue {
  size: string;
  key: string;
  label: string;
  problem: "missing" | "not_a_number" | "implausible";
  detail: string;
}

export interface ChartValidation {
  /** Blocking problems: the chart cannot be trusted until these are gone. */
  issues: FieldIssue[];
  /** Shopify sizes with no row at all. */
  missingSizes: string[];
  /** Rows for sizes that no Shopify variant uses. */
  extraSizes: string[];
  /** Rows whose values don't increase with size — usually a paste in the wrong order. */
  orderingWarnings: string[];
  valid: boolean;
}

/**
 * Validate a chart against the category's required fields and the product's
 * actual Shopify sizes. This is what "complete" has to mean.
 */
export function validateChart(
  rows: SizeRow[],
  category: GarmentCategory,
  shopifySizes: string[],
  referenceSize?: string,
): ChartValidation {
  const fields = MEASUREMENT_FIELDS[category];
  const issues: FieldIssue[] = [];
  const seen = new Set<string>();

  for (const row of rows) {
    if (seen.has(row.size)) {
      issues.push({
        size: row.size, key: "size", label: "Size",
        problem: "not_a_number", detail: `"${row.size}" appears more than once.`,
      });
    }
    seen.add(row.size);

    for (const f of fields) {
      const raw = row.values[f.key];
      if (raw === undefined || raw === null || (raw as unknown) === "") {
        issues.push({
          size: row.size, key: f.key, label: f.label,
          problem: "missing", detail: `${f.label} is empty for size ${row.size}.`,
        });
        continue;
      }
      if (typeof raw !== "number" || Number.isNaN(raw)) {
        issues.push({
          size: row.size, key: f.key, label: f.label,
          problem: "not_a_number", detail: `${f.label} for size ${row.size} isn't a number.`,
        });
        continue;
      }
      const [min, max] = RANGE_CM[f.key] ?? [1, 300];
      if (raw < min || raw > max) {
        issues.push({
          size: row.size, key: f.key, label: f.label,
          problem: "implausible",
          detail: `${f.label} for size ${row.size} is ${raw} cm, outside the plausible ${min}–${max} cm. Check the units.`,
        });
      }
    }
  }

  const chartSizes = rows.map((r) => r.size);
  const missingSizes = shopifySizes.filter((s) => !chartSizes.includes(s));
  const extraSizes = chartSizes.filter((s) => !shopifySizes.includes(s));
  if (referenceSize && !chartSizes.includes(referenceSize)) {
    missingSizes.push(referenceSize);
  }

  // Sizes are ordered as Shopify returns them, so a graded measurement should
  // move monotonically down the column. A column that jumps around is usually
  // a chart pasted in a different order than the size list.
  const orderingWarnings: string[] = [];
  const ordered = shopifySizes
    .map((s) => rows.find((r) => r.size === s))
    .filter((r): r is SizeRow => Boolean(r));
  for (const f of fields) {
    const series = ordered
      .map((r) => r.values[f.key])
      .filter((v): v is number => typeof v === "number");
    if (series.length < 3) continue;
    const up = series.every((v, i) => i === 0 || v >= series[i - 1]);
    const down = series.every((v, i) => i === 0 || v <= series[i - 1]);
    if (!up && !down) orderingWarnings.push(f.label);
  }

  return {
    issues,
    missingSizes: [...new Set(missingSizes)],
    extraSizes,
    orderingWarnings,
    valid: issues.length === 0 && missingSizes.length === 0 && rows.length > 0,
  };
}

// ------------------------------------------------------------------ import

export interface ParsedChart {
  rows: SizeRow[];
  /** Header cells that matched nothing this category asks for. */
  unmappedColumns: string[];
  /** Category fields no column supplied. */
  unmatchedFields: string[];
  rowCount: number;
}

export interface ParseError {
  error: string;
}

const HEADER_ALIASES: Record<string, string> = {
  bust: "bust", chest: "chest", "chest width": "chest", "bust width": "bust",
  waist: "waist", "natural waist": "waist",
  hip: "hip", hips: "hip", "hip width": "hip",
  shoulder: "shoulder", "shoulder width": "shoulder", "across shoulder": "shoulder",
  length: "length", "body length": "length", "total length": "length",
  sleeve: "sleeve", "sleeve length": "sleeve",
  armhole: "armhole", rise: "rise", "front rise": "rise",
  inseam: "inseam", "inside leg": "inseam",
  outseam: "outseam", "outside leg": "outseam",
  thigh: "thigh", "leg opening": "legOpening", legopening: "legOpening",
  hem: "hem", "hem width": "hem", width: "width",
};

function splitLine(line: string, delimiter: string): string[] {
  // Enough CSV for a size chart: quoted cells with embedded delimiters.
  const out: string[] = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (quoted && line[i + 1] === '"') { cell += '"'; i++; }
      else quoted = !quoted;
    } else if (ch === delimiter && !quoted) {
      out.push(cell);
      cell = "";
    } else {
      cell += ch;
    }
  }
  out.push(cell);
  return out.map((c) => c.trim());
}

/**
 * Parse a pasted or uploaded CSV/TSV size chart into rows, in centimetres.
 *
 * The result is a *preview*: nothing is applied to a garment until the
 * merchant has seen the mapping and confirmed it.
 */
export function parseChart(
  text: string,
  category: GarmentCategory,
  unit: Unit,
): ParsedChart | ParseError {
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);
  if (lines.length < 2) {
    return { error: "Need a header row and at least one size row." };
  }
  const delimiter = lines[0].includes("\t") ? "\t" : lines[0].includes(";") ? ";" : ",";
  const header = splitLine(lines[0], delimiter);
  if (header.length < 2) {
    return { error: "Couldn't find columns — check it's comma, semicolon or tab separated." };
  }

  const fields = MEASUREMENT_FIELDS[category];
  const validKeys = new Set(fields.map((f) => f.key));
  const unmappedColumns: string[] = [];
  const columnKeys = header.map((h, i) => {
    if (i === 0) return "__size";
    const norm = h
      .toLowerCase()
      .replace(/\((cm|in|inches|centimetres)\)/g, "")
      .replace(/[^a-z ]/g, "")
      .trim();
    const key = HEADER_ALIASES[norm] ?? norm.replace(/\s+/g, "");
    if (!validKeys.has(key)) {
      if (h) unmappedColumns.push(h);
      return null;
    }
    return key;
  });

  const rows: SizeRow[] = [];
  for (const line of lines.slice(1)) {
    const cells = splitLine(line, delimiter);
    const size = cells[0];
    if (!size) continue;
    const values: Record<string, number | undefined> = {};
    cells.forEach((cell, i) => {
      const key = columnKeys[i];
      if (!key || key === "__size") return;
      const n = Number(cell.replace(/[^0-9.-]/g, ""));
      // A blank cell stays undefined — validation reports it as missing rather
      // than substituting a number nobody supplied.
      if (cell !== "" && !Number.isNaN(n)) values[key] = toCm(n, unit);
    });
    rows.push({ size, values });
  }
  if (rows.length === 0) return { error: "No size rows found below the header." };

  const supplied = new Set(columnKeys.filter((k): k is string => Boolean(k) && k !== "__size"));
  return {
    rows,
    unmappedColumns,
    unmatchedFields: fields.filter((f) => !supplied.has(f.key)).map((f) => f.label),
    rowCount: rows.length,
  };
}

/** An empty, correctly-shaped grid for manual entry. Empty, not pre-filled. */
export function blankRows(sizes: string[], category: GarmentCategory): SizeRow[] {
  const fields = MEASUREMENT_FIELDS[category];
  return sizes.map((size) => ({
    size,
    values: Object.fromEntries(fields.map((f) => [f.key, undefined])),
  }));
}

/**
 * Apply a brand chart's grading rules to a measured reference size.
 *
 * This is the one derivation that is legitimate, because the merchant supplied
 * both halves: the measured reference row, and their own per-step increments.
 * Anything it produces is still marked as `rules`, never as measured.
 */
export function gradeFromRules(
  referenceRow: SizeRow,
  sizes: string[],
  rules: Record<string, number>,
): SizeRow[] {
  const refIndex = sizes.indexOf(referenceRow.size);
  if (refIndex < 0) return [];
  return sizes.map((size, i) => {
    if (size === referenceRow.size) return { size, values: { ...referenceRow.values } };
    const steps = i - refIndex;
    const values: Record<string, number | undefined> = {};
    for (const [key, base] of Object.entries(referenceRow.values)) {
      if (typeof base !== "number") continue;
      const increment = rules[key];
      // No rule for this measurement means no honest way to grade it.
      values[key] = increment === undefined ? undefined : Math.round((base + increment * steps) * 10) / 10;
    }
    return { size, values };
  });
}
