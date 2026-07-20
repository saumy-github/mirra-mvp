import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { getRuntimeProvider, MirraApiError, userMessage } from "@/integrations/mirra-api";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { MirraMark } from "@/components/ui/logo";

/** Accessibility fallback: type the short pairing code instead of scanning. */
export default function Capture() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    const code = String(new FormData(e.currentTarget).get("code") ?? "");
    try {
      const { token } = await getRuntimeProvider().resolveManualCode(code);
      navigate(`/capture/${token}`);
    } catch (err) {
      setError(err instanceof MirraApiError ? userMessage(err.code) : "That code didn't work.");
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-6">
      <MirraMark size={30} className="text-ink" />
      <div className="mt-8 w-full max-w-xs text-center">
        <h1 className="text-xl font-semibold tracking-tight">Enter pairing code</h1>
        <p className="mt-2 text-sm text-muted">
          The six-character code is shown under the QR on your computer.
        </p>
        <form onSubmit={onSubmit} className="mt-6 space-y-3" noValidate>
          <Field
            label="Pairing code"
            hideLabel
            name="code"
            placeholder="ABC123"
            autoComplete="off"
            autoCapitalize="characters"
            maxLength={6}
            className="text-center font-mono tracking-[0.4em] uppercase"
            required
          />
          {error && (
            <p role="alert" className="text-sm text-error">
              {error}
            </p>
          )}
          <Button type="submit" size="lg" className="w-full" loading={busy}>
            Connect
          </Button>
        </form>
      </div>
    </main>
  );
}
