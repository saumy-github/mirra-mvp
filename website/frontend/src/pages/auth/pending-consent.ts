// Bridges consent across the Google redirect — see doc 06.
const PENDING_CONSENT_KEY = "mirra_pending_consent";

export function markPendingConsent(): void {
  try {
    sessionStorage.setItem(PENDING_CONSENT_KEY, "1");
  } catch {
    // Unavailable (e.g. private browsing) — consent just won't be recorded.
  }
}

export function consumePendingConsent(): boolean {
  try {
    const had = sessionStorage.getItem(PENDING_CONSENT_KEY) === "1";
    sessionStorage.removeItem(PENDING_CONSENT_KEY);
    return had;
  } catch {
    return false;
  }
}
