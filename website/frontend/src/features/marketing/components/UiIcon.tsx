import type { CSSProperties } from "react";

export const UI_ICON_NAMES = [
  "arrow-up-right",
  "menu",
  "close",
  "mail",
  "spark",
  "plus",
] as const;

export type UiIconName = (typeof UI_ICON_NAMES)[number];

export type UiIconProps = {
  className?: string;
  label?: string;
  name: UiIconName;
  size?: number | string;
  strokeWidth?: number;
  style?: CSSProperties;
};

const part: CSSProperties = {
  boxSizing: "border-box",
  display: "block",
  position: "absolute",
};

/**
 * A small, dependency-free icon set drawn entirely with CSS geometry.
 * Icons are decorative by default; pass `label` only when the icon itself
 * needs an accessible name instead of inheriting one from its control.
 */
export function UiIcon({
  className,
  label,
  name,
  size = 16,
  strokeWidth = 1.5,
  style,
}: UiIconProps) {
  const stroke = `${strokeWidth}px solid currentColor`;
  const line: CSSProperties = {
    ...part,
    background: "currentColor",
    borderRadius: 999,
    height: strokeWidth,
  };

  return (
    <i
      aria-hidden={label ? undefined : true}
      aria-label={label}
      className={className}
      data-ui-icon={name}
      role={label ? "img" : undefined}
      style={{
        color: "inherit",
        display: "inline-block",
        flex: "0 0 auto",
        fontStyle: "normal",
        height: size,
        pointerEvents: "none",
        position: "relative",
        verticalAlign: "-0.125em",
        width: size,
        ...style,
      }}
    >
      {name === "arrow-up-right" && (
        <>
          <i
            style={{
              ...line,
              left: "14%",
              top: "48%",
              transform: "rotate(-45deg)",
              transformOrigin: "center",
              width: "72%",
            }}
          />
          <i
            style={{
              ...part,
              borderRight: stroke,
              borderTop: stroke,
              height: "42%",
              right: "10%",
              top: "10%",
              width: "42%",
            }}
          />
        </>
      )}

      {name === "menu" && (
        <>
          <i style={{ ...line, left: "9%", top: "31%", width: "82%" }} />
          <i style={{ ...line, left: "9%", top: "67%", width: "82%" }} />
        </>
      )}

      {name === "close" && (
        <>
          <i
            style={{
              ...line,
              left: "9%",
              top: "48%",
              transform: "rotate(45deg)",
              width: "82%",
            }}
          />
          <i
            style={{
              ...line,
              left: "9%",
              top: "48%",
              transform: "rotate(-45deg)",
              width: "82%",
            }}
          />
        </>
      )}

      {name === "mail" && (
        <>
          <i
            style={{
              ...part,
              border: stroke,
              borderRadius: Math.max(2, strokeWidth),
              height: "60%",
              left: "7%",
              top: "21%",
              width: "86%",
            }}
          />
          <i
            style={{
              ...line,
              left: "11%",
              top: "29%",
              transform: "rotate(31deg)",
              transformOrigin: "left center",
              width: "47%",
            }}
          />
          <i
            style={{
              ...line,
              right: "11%",
              top: "29%",
              transform: "rotate(-31deg)",
              transformOrigin: "right center",
              width: "47%",
            }}
          />
        </>
      )}

      {name === "spark" && (
        <>
          <i
            style={{
              ...part,
              background: "currentColor",
              clipPath: "polygon(50% 0, 58% 42%, 100% 50%, 58% 58%, 50% 100%, 42% 58%, 0 50%, 42% 42%)",
              height: "72%",
              left: "6%",
              top: "22%",
              width: "72%",
            }}
          />
          <i
            style={{
              ...part,
              background: "currentColor",
              clipPath: "polygon(50% 0, 60% 40%, 100% 50%, 60% 60%, 50% 100%, 40% 60%, 0 50%, 40% 40%)",
              height: "32%",
              right: "2%",
              top: "2%",
              width: "32%",
            }}
          />
        </>
      )}

      {name === "plus" && (
        <>
          <i style={{ ...line, left: "9%", top: "48%", width: "82%" }} />
          <i
            style={{
              ...line,
              left: "9%",
              top: "48%",
              transform: "rotate(90deg)",
              width: "82%",
            }}
          />
        </>
      )}
    </i>
  );
}
