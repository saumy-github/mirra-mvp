export function MirraBrand({ compact = false }: { compact?: boolean }) {
  return (
    <span className={`mirra-brand${compact ? " mirra-brand--compact" : ""}`}>
      <span className="mirra-mark" aria-hidden="true">
        {Array.from({ length: 6 }, (_, index) => <i key={index} />)}
      </span>
      <span>Mirra</span>
    </span>
  );
}

export function ProfileGlyph() {
  return <span className="nav-avatar" aria-hidden="true" />;
}
