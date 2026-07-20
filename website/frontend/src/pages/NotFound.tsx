import { ErrorScreen } from "@/components/ui/error-screen";

export default function NotFound() {
  return (
    <ErrorScreen
      code="NOT_FOUND"
      title="This page doesn't exist"
      body="The link may be out of date, or the page may have moved."
      action={{ to: "/", label: "Back home" }}
    />
  );
}
