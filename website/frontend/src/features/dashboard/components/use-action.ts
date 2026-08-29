import { useEffect, useRef, useState } from "react";
import type { ActionResult } from "../data/actions";

export type NoticeTone = "success" | "danger";
export interface Notice {
  tone: NoticeTone;
  message: string;
}

/**
 * The shared mutation lifecycle: idle → pending → success | error, with the
 * result announced rather than swallowed.
 *
 * Every action returns an `ActionResult`; before this hook existed those
 * results were discarded at the call site, so a refused transition produced a
 * button that appeared to do nothing at all.
 */
export function useAction() {
  const [pending, setPending] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const alive = useRef(true);
  useEffect(() => () => { alive.current = false; }, []);

  const run = (fn: () => ActionResult, onSuccess?: (message?: string) => void) => {
    if (pending) return; // guards the double-click that would submit twice
    setPending(true);
    try {
      const result = fn();
      if (!alive.current) return;
      if (result.ok) {
        setNotice(result.message ? { tone: "success", message: result.message } : null);
        onSuccess?.(result.message);
      } else {
        setNotice({ tone: "danger", message: result.error });
      }
    } catch (e) {
      setNotice({ tone: "danger", message: e instanceof Error ? e.message : "Something went wrong." });
    } finally {
      if (alive.current) setPending(false);
    }
  };

  return { pending, notice, setNotice, run, clear: () => setNotice(null) };
}
