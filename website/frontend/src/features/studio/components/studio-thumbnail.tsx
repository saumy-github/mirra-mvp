export function StudioThumbnail({
  src,
  label,
  className = "",
  fit = "contain",
}: {
  src: string | null | undefined;
  label: string;
  className?: string;
  fit?: "contain" | "cover";
}) {
  if (src) {
    return (
      <img
        src={src}
        alt=""
        draggable={false}
        decoding="async"
        className={`${className} ${fit === "cover" ? "object-cover" : "object-contain"}`}
      />
    );
  }

  const initials = label
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase();

  return (
    <span
      aria-hidden
      className={`${className} flex items-center justify-center bg-[radial-gradient(circle_at_32%_24%,rgba(255,255,255,.9),transparent_42%),linear-gradient(145deg,rgba(239,236,230,.96),rgba(222,217,209,.88))] font-mono text-[10px] font-medium tracking-[0.12em] text-muted uppercase`}
    >
      {initials || "—"}
    </span>
  );
}
