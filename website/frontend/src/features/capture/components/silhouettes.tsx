/** Pose silhouette guides overlaid on the camera preview. */
export function PoseSilhouette({
  pose,
  className = "",
}: {
  pose: "front" | "side" | "back";
  className?: string;
}) {
  const common = {
    stroke: "rgba(255,255,255,0.85)",
    strokeWidth: 2,
    strokeDasharray: "6 7",
    fill: "none",
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  return (
    <svg viewBox="0 0 200 400" className={className} aria-hidden>
      {pose === "front" || pose === "back" ? (
        <g {...common}>
          <circle cx="100" cy="42" r="20" />
          <path d="M100 62 v10" />
          <path d="M72 80 C60 84 54 96 52 112 C50 140 52 168 56 190 M128 80 C140 84 146 96 148 112 C150 140 148 168 144 190" />
          <path d="M72 80 C90 74 110 74 128 80 C132 110 132 150 126 190 C124 204 76 204 74 190 C68 150 68 110 72 80 Z" />
          <path d="M78 202 C76 250 78 300 84 348 M122 202 C124 250 122 300 116 348" />
          <path d="M84 348 h18 M116 348 h-18 M100 210 v130" />
        </g>
      ) : (
        <g {...common}>
          <circle cx="104" cy="42" r="20" />
          <path d="M102 62 v10" />
          <path d="M92 80 C82 90 78 110 80 140 C81 165 86 185 92 196 C104 202 116 200 120 194 C124 160 124 110 116 80 C108 74 98 76 92 80 Z" />
          <path d="M108 84 C112 110 112 150 108 190" />
          <path d="M94 202 C92 250 94 300 98 348 M114 202 C114 250 112 300 108 348" />
          <path d="M98 348 h16" />
        </g>
      )}
    </svg>
  );
}
