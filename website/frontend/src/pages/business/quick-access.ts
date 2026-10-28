import { businessDestination } from "./destination";

export const businessQuickAccessEnabled = import.meta.env.DEV;

export async function enterBusinessDemo(next?: string | null): Promise<string> {
  if (!businessQuickAccessEnabled) throw new Error("Quick Access is only available in development.");

  const { signIn } = await import("@/features/dashboard/data/session");
  signIn("u_owner");

  const destination = new URL(businessDestination(next), "https://mirra.local");
  // Start requires real merchant auth; the demo already has its workspace.
  if (destination.pathname === "/dashboard/start") destination.pathname = "/dashboard/portal";
  return `${destination.pathname}${destination.search}${destination.hash}`;
}
