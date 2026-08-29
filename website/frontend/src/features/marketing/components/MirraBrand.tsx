import { MirraLogo } from "@/components/ui/logo";

export function MirraBrand({ compact = false }: { compact?: boolean }) {
  return (
    <span className={`mirra-brand${compact ? " mirra-brand--compact" : ""}`}>
      <MirraLogo alt="" className="mirra-brand__asset" height={compact ? 30 : 38} />
    </span>
  );
}

export function ProfileGlyph() {
  return <span className="nav-avatar" aria-hidden="true" />;
}
