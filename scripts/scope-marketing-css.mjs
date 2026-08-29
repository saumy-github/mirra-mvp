/**
 * Scopes the redesign's global stylesheet to the marketing route subtree.
 *
 * The redesign was authored as a standalone site, so its stylesheet owns
 * `html`/`body`/`:root` and sets a dark theme. The app (studio, profile,
 * onboarding, auth) is light-themed and shares `src/styles/globals.css`, so
 * letting the redesign's rules land globally would restyle all 16 app routes.
 *
 * This rewrites the sheet so every rule is nested under `.mirra-landing`,
 * which MarketingLayout puts on its wrapper. Document-level rules are folded
 * into that wrapper; only genuinely inert at-rules stay global.
 *
 * Usage: node scripts/scope-marketing-css.mjs <source.css> <dest.css>
 */
import { readFileSync, writeFileSync } from "node:fs";

const SCOPE = ".mirra-landing";
const [, , SRC, DEST] = process.argv;
if (!SRC || !DEST) {
  console.error("usage: scope-marketing-css.mjs <source.css> <dest.css>");
  process.exit(1);
}

const css = readFileSync(SRC, "utf8");

/** Split a stylesheet into top-level blocks, respecting braces, strings and
 * comments. Returns `{ prelude, body, raw }` for blocks and `{ raw }` for
 * statements that end in a semicolon (e.g. `@import`). */
function splitTopLevel(input) {
  const out = [];
  let depth = 0;
  let start = 0;
  let preludeEnd = -1;
  let inString = null;
  let inComment = false;

  for (let i = 0; i < input.length; i++) {
    const c = input[i];
    const next = input[i + 1];

    if (inComment) {
      if (c === "*" && next === "/") inComment = false, i++;
      continue;
    }
    if (inString) {
      if (c === "\\") i++;
      else if (c === inString) inString = null;
      continue;
    }
    if (c === "/" && next === "*") {
      inComment = true;
      i++;
      continue;
    }
    if (c === '"' || c === "'") {
      inString = c;
      continue;
    }

    if (c === "{") {
      if (depth === 0) preludeEnd = i;
      depth++;
    } else if (c === "}") {
      depth--;
      if (depth === 0) {
        const raw = input.slice(start, i + 1);
        out.push({
          prelude: input.slice(start, preludeEnd).trim(),
          body: input.slice(preludeEnd + 1, i).trim(),
          raw,
        });
        start = i + 1;
      }
    } else if (c === ";" && depth === 0) {
      const raw = input.slice(start, i + 1).trim();
      if (raw) out.push({ raw, statement: true });
      start = i + 1;
    }
  }
  const tail = input.slice(start).trim();
  if (tail) out.push({ raw: tail, statement: true });
  return out;
}

const blocks = splitTopLevel(css);

const hoisted = []; // stays at top level
const wrapperDecls = []; // folded into `.mirra-landing { ... }`
const nested = []; // nested inside `.mirra-landing`
const warnings = [];

/** Rules whose selector targets the document itself. Their declarations move
 * onto the marketing wrapper element instead. */
const isDocumentSelector = (s) => /^(html|body|:root)$/.test(s.trim());

for (const b of blocks) {
  if (b.statement) {
    // @import / @charset — must stay at top level.
    hoisted.push(b.raw);
    continue;
  }

  // A rule's prelude carries any comment that preceded it; strip those so
  // selector matching sees the selector alone.
  const leading = [];
  const p = b.prelude
    .replace(/\/\*[\s\S]*?\*\//g, (m) => (leading.push(m), ""))
    .trim();
  const comment = leading.length ? `${leading.join("\n")}\n` : "";

  // @font-face only declares a family; it applies nothing on its own, so it
  // is safe (and necessary) at top level. @keyframes names were checked
  // against globals.css and do not collide.
  if (/^@(font-face|keyframes|charset|import|supports)/i.test(p)) {
    hoisted.push(b.raw);
    continue;
  }

  // Lenis is mounted only by MarketingLayout and torn down on unmount, so
  // these html-level rules are only live while on a marketing route.
  if (/^html\.lenis/i.test(p)) {
    hoisted.push(
      `${comment}/* Lenis is mounted only by MarketingLayout and destroyed on unmount, so\n` +
        `   these html-level rules are live only on marketing routes. */\n` +
        `${p} {\n${b.body}\n}`,
    );
    continue;
  }

  const selectors = p.split(",").map((s) => s.trim()).filter(Boolean);

  // Pure document-level rule: fold its declarations onto the wrapper.
  if (selectors.every(isDocumentSelector)) {
    wrapperDecls.push(`  /* from \`${p}\` */`);
    for (const line of b.body.split("\n")) {
      const t = line.trim();
      if (t) wrapperDecls.push(`  ${t}`);
    }
    continue;
  }

  // Mixed rule such as `body, button, input`: keep the non-document parts as
  // descendants, and fold the document part onto the wrapper.
  if (selectors.some(isDocumentSelector)) {
    const docParts = selectors.filter(isDocumentSelector);
    const rest = selectors.filter((s) => !isDocumentSelector(s));
    wrapperDecls.push(`  /* from \`${docParts.join(", ")}\` (split from \`${p}\`) */`);
    for (const line of b.body.split("\n")) {
      const t = line.trim();
      if (t) wrapperDecls.push(`  ${t}`);
    }
    nested.push(indent(`${rest.join(",\n")} {\n${b.body}\n}`));
    continue;
  }

  // Anything still naming html/body inside a compound selector would not
  // match once nested under a <div>. Surface it rather than silently break.
  if (/(^|[\s>+~(])(html|body)([\s.:[#>+~,)]|$)/i.test(p)) {
    warnings.push(p.replace(/\s+/g, " ").slice(0, 100));
  }

  nested.push(indent(b.raw));
}

function indent(text) {
  return text
    .split("\n")
    .map((l) => (l.trim() ? `  ${l}` : l))
    .join("\n");
}

const header = `/*
 * Marketing / landing design system — ported verbatim from the standalone
 * redesign, then scoped to \`${SCOPE}\`.
 *
 * GENERATED by scripts/scope-marketing-css.mjs. To re-sync with the redesign,
 * re-run that script rather than hand-editing this file.
 *
 * Scoping matters: the redesign is dark-themed and owned \`html\`/\`body\`, while
 * the app routes are light-themed and share src/styles/globals.css. Nothing
 * here may leak outside the marketing route subtree.
 */
`;

const output = [
  header,
  hoisted.join("\n\n"),
  "",
  `${SCOPE} {`,
  wrapperDecls.join("\n"),
  "",
  nested.join("\n\n"),
  `}`,
  "",
].join("\n");

writeFileSync(DEST, output);

console.log(`hoisted at top level : ${hoisted.length}`);
console.log(`folded onto wrapper  : ${wrapperDecls.filter((l) => !l.includes("/*")).length} decls`);
console.log(`nested under scope   : ${nested.length}`);
console.log(`wrote ${DEST}`);
if (warnings.length) {
  console.log(`\n!! ${warnings.length} selector(s) still reference html/body and need review:`);
  for (const w of warnings) console.log(`   ${w}`);
}
