import { useSearchParams } from "react-router-dom";
import { ErrorScreen } from "@/components/ui/error-screen";

export default function ProductUnavailable() {
  const [params] = useSearchParams();
  const isDegraded = params.get("degraded") === "1";
  return (
    <ErrorScreen
      code={isDegraded ? "SERVICE_UNAVAILABLE" : "ITEM_UNAVAILABLE"}
      title={
        isDegraded
          ? "The fitting room is briefly unavailable"
          : "This item isn't available to try on"
      }
      body={
        isDegraded
          ? "Something went wrong while preparing the session. Give it a moment and try again."
          : "This garment may have been paused or removed from the catalogue. You can still browse everything else in the studio."
      }
      action={{ to: "/studio", label: "Back to the studio" }}
    />
  );
}
