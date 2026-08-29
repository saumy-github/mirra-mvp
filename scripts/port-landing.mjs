/**
 * Copies the landing overhaul's source into this repo and applies the
 * mechanical framework rewrites (App Router / RSC -> Vite SPA on
 * react-router-dom). Anything requiring judgement — auth wiring, Lenis
 * reconciliation — is left alone and handled in follow-up edits.
 *
 * Usage: node scripts/port-landing.mjs <redesign-root>
 */
import { readFileSync, writeFileSync, mkdirSync, copyFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

const SRC = process.argv[2];
if (!SRC) {
  console.error("usage: port-landing.mjs <redesign-root>");
  process.exit(1);
}
const DEST = resolve("website/frontend/src");

/** [from, to] relative to redesign root / this repo's src. */
const FILES = [
  ["app/mirra-content.ts", "features/marketing/content.ts"],
  ["app/components/SiteNavbar.tsx", "features/marketing/components/SiteNavbar.tsx"],
  ["app/components/SiteFooter.tsx", "features/marketing/components/SiteFooter.tsx"],
  ["app/components/SiteChrome.tsx", "features/marketing/components/SiteChrome.tsx"],
  ["app/components/SmoothNavigation.tsx", "features/marketing/components/SmoothNavigation.tsx"],
  ["app/components/LiquidCTA.tsx", "features/marketing/components/LiquidCTA.tsx"],
  ["app/components/MirraBrand.tsx", "features/marketing/components/MirraBrand.tsx"],
  ["app/components/UiIcon.tsx", "features/marketing/components/UiIcon.tsx"],
  ["app/page.tsx", "pages/Home.tsx"],
  ["app/pricing/PricingClient.tsx", "pages/Pricing.tsx"],
  ["app/pricing/pricing.module.css", "pages/pricing.module.css"],
  ["app/faq/FAQClient.tsx", "pages/FAQ.tsx"],
  ["app/faq/faq.module.css", "pages/faq.module.css"],
];

/** Rewrites applied to every ported .ts/.tsx file. */
function transform(code, destRel) {
  let out = code;
  const notes = [];

  // Every route in this app is client-rendered; the directive is a no-op here
  // and React would warn about it.
  out = out.replace(/^["']use client["'];?\n+/m, "");

  // Same library, current import path. This repo already depends on `motion`.
  out = out.replace(/from "framer-motion"/g, 'from "motion/react"');

  // App Router primitives -> react-router-dom.
  out = out.replace(/^import Link from "next\/link";\n/m, "");
  out = out.replace(
    /^import \{([^}]*)\} from "next\/navigation";\n/m,
    (_, names) => {
      notes.push(`next/navigation: ${names.trim()}`);
      return "";
    },
  );

  // <Link href> -> <Link to>, without touching plain <a href>.
  out = out.replace(/<Link\b[^>]*>/g, (tag) => tag.replace(/\bhref=/g, "to="));

  // usePathname() -> useLocation().pathname; useRouter().push -> navigate.
  const usesPathname = /\busePathname\(\)/.test(out);
  const usesRouter = /\buseRouter\(\)/.test(out);
  out = out.replace(/\busePathname\(\)/g, "useLocation().pathname");
  out = out.replace(/const router = useRouter\(\);/g, "const navigate = useNavigate();");
  out = out.replace(/router\.push\(/g, "navigate(");
  out = out.replace(/router\.replace\(/g, "navigate(");

  // Rebuild the react-router import from what the file actually uses.
  const needed = [];
  if (/<Link\b/.test(out)) needed.push("Link");
  if (usesPathname) needed.push("useLocation");
  if (usesRouter) needed.push("useNavigate");
  if (needed.length) {
    const imp = `import { ${needed.join(", ")} } from "react-router-dom";\n`;
    // Place it after the last existing import so ordering stays sane.
    const lastImport = [...out.matchAll(/^import .*;\n/gm)].pop();
    out = lastImport
      ? out.slice(0, lastImport.index + lastImport[0].length) +
        imp +
        out.slice(lastImport.index + lastImport[0].length)
      : imp + out;
  }

  // Local module specifiers change shape once files move.
  out = out.replace(/from "\.\.\/mirra-content"/g, 'from "../content"');
  out = out.replace(/from "\.\/mirra-content"/g, 'from "./features/marketing/content"');
  out = out.replace(/from "\.\/components\//g, 'from "@/features/marketing/components/');
  out = out.replace(/from "\.\.\/components\//g, 'from "@/features/marketing/components/');

  return { out, notes };
}

mkdirSync(`${DEST}/features/marketing/components`, { recursive: true });

for (const [from, to] of FILES) {
  const srcPath = resolve(SRC, from);
  const destPath = `${DEST}/${to}`;
  mkdirSync(dirname(destPath), { recursive: true });

  if (from.endsWith(".css")) {
    copyFileSync(srcPath, destPath);
    console.log(`copied   ${to}`);
    continue;
  }

  const { out, notes } = transform(readFileSync(srcPath, "utf8"), to);
  writeFileSync(destPath, out);
  console.log(`ported   ${to}${notes.length ? `   [${notes.join("; ")}]` : ""}`);
}
