// In-memory store for the dashboard prototype, seeded on first read.
//
// The standalone prototype persisted this to a JSON file on the Node side
// (`.data/db.json`) and re-read it per request. In the SPA there is no server,
// so the same `Db` shape lives in module state and components subscribe to it.
// Mutations are still funnelled through `updateDb` so the seam to the real
// backend stays exactly where it was: swap these four functions for calls to
// `@/integrations/mirra-api` and every page above keeps working.
//
// Deliberately NOT persisted to localStorage: the seed is ~5k analytics events,
// and a reload giving you a clean, known dataset is what you want from a demo.
import { useSyncExternalStore } from "react";
import type { Db } from "./types";
import { buildSeed } from "./seed";

let db: Db | null = null;
let version = 0;
const listeners = new Set<() => void>();

function emit() {
  version += 1;
  for (const l of listeners) l();
}

export function getDb(): Db {
  if (!db) db = buildSeed();
  return db;
}

/** Mutate the DB inside `fn`, then notify subscribers. */
export function updateDb<T>(fn: (db: Db) => T): T {
  const result = fn(getDb());
  emit();
  return result;
}

export function resetDb() {
  db = buildSeed();
  emit();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/**
 * Re-render this component whenever the store changes. Pages call it for the
 * subscription; they keep reading through `getDb()` and the query helpers,
 * which is why the returned value is just a version counter.
 */
export function useDbVersion(): number {
  return useSyncExternalStore(
    subscribe,
    () => version,
    () => version,
  );
}

// Vite keeps module singletons alive across hot updates, so an edit to
// `seed.ts` would leave the old dataset in memory and the screen showing
// garments that no longer exist. Drop it on every hot update.
if (import.meta.hot) {
  import.meta.hot.accept(() => {
    db = null;
    emit();
  });
  import.meta.hot.dispose(() => {
    db = null;
  });
}

let idCounter = 0;
export function newId(prefix: string): string {
  idCounter = (idCounter + 1) % 1000;
  return `${prefix}_${Date.now().toString(36)}${idCounter.toString(36)}`;
}
