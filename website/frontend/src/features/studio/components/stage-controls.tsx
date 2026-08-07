import type { ReactNode } from "react";

export const ZOOM_MIN = 0.8;
export const ZOOM_MAX = 1.4;
export const ZOOM_STEP = 0.1;

/**
 * Zoom out · fit · zoom in. One hairline group, three quiet glyphs —
 * the controls should be findable, not noticeable.
 */
export function StageControls({
  zoom,
  onZoomChange,
}: {
  zoom: number;
  onZoomChange: (zoom: number) => void;
}) {
  const round = (value: number) => +value.toFixed(3);

  return (
    <div
      role="group"
      aria-label="View controls"
      className="flex items-center divide-x divide-hairline overflow-hidden rounded-panel-sm border border-hairline bg-vellum"
    >
      <StageControl
        label="Zoom out"
        disabled={zoom <= ZOOM_MIN}
        onClick={() => onZoomChange(round(Math.max(ZOOM_MIN, zoom - ZOOM_STEP)))}
      >
        <svg viewBox="0 0 16 16" className="size-3.5" stroke="currentColor" strokeWidth="1.2">
          <path d="M4 8h8" strokeLinecap="round" />
        </svg>
      </StageControl>

      <StageControl label="Fit to frame" onClick={() => onZoomChange(1)}>
        <svg
          viewBox="0 0 16 16"
          className="size-3.5"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M5.5 2.5H2.5V5.5M10.5 2.5h3v3M5.5 13.5H2.5v-3M10.5 13.5h3v-3" />
        </svg>
      </StageControl>

      <StageControl
        label="Zoom in"
        disabled={zoom >= ZOOM_MAX}
        onClick={() => onZoomChange(round(Math.min(ZOOM_MAX, zoom + ZOOM_STEP)))}
      >
        <svg viewBox="0 0 16 16" className="size-3.5" stroke="currentColor" strokeWidth="1.2">
          <path d="M4 8h8M8 4v8" strokeLinecap="round" />
        </svg>
      </StageControl>
    </div>
  );
}

function StageControl({
  label,
  onClick,
  disabled,
  children,
}: {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      className="flex size-9 items-center justify-center text-slate transition-colors hover:bg-bone hover:text-graphite disabled:pointer-events-none disabled:opacity-30"
    >
      {children}
    </button>
  );
}
