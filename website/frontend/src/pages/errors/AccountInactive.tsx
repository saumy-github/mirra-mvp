import { useSearchParams } from "react-router-dom";
import { ErrorScreen } from "@/components/ui/error-screen";

const COPY: Record<string, { title: string; body: string }> = {
  suspended: {
    title: "Your account is inactive",
    body: "This account can't start new try-on sessions right now. Contact support if you think this is a mistake.",
  },
  maintenance: {
    title: "Back shortly",
    body: "Mirra is undergoing brief maintenance. Try again in a few minutes.",
  },
  try_on_disabled: {
    title: "Try-on is switched off",
    body: "Virtual try-on is temporarily disabled for this account.",
  },
};

export default function AccountInactive() {
  const [params] = useSearchParams();
  const copy = COPY[params.get("reason") ?? ""] ?? COPY.suspended;
  return (
    <ErrorScreen code="SESSION_UNAVAILABLE" title={copy.title} body={copy.body} action={null} />
  );
}
