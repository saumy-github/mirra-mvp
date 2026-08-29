export type MirraLogoVariant = "dark" | "light";

const MIRRA_LOGO_ASSETS: Record<MirraLogoVariant, { mark: string; lockup: string }> = {
  dark: {
    mark: "/brand/Mirra-logo-dark.png",
    lockup: "/brand/mirra-logo-dark-long.png",
  },
  light: {
    mark: "/brand/Mirra-logo-light.png",
    lockup: "/brand/mirra-logo-light-long.png",
  },
};

type LogoImageProps = {
  alt?: string;
  className?: string;
  variant?: MirraLogoVariant;
};

export function MirraMark({
  alt = "",
  className = "",
  size = 30,
  variant = "dark",
}: LogoImageProps & {
  size?: number;
  /** Kept for compatibility with the previous drawn mark. */
  strokeWidth?: number;
}) {
  return (
    <img
      src={MIRRA_LOGO_ASSETS[variant].mark}
      alt={alt}
      aria-hidden={alt ? undefined : true}
      draggable={false}
      width={size}
      height={size}
      className={`shrink-0 object-contain ${className}`.trim()}
    />
  );
}

export function MirraLogo({
  alt = "Mirra",
  className = "",
  height = 40,
  variant = "dark",
}: LogoImageProps & { height?: number }) {
  return (
    <img
      src={MIRRA_LOGO_ASSETS[variant].lockup}
      alt={alt}
      aria-hidden={alt ? undefined : true}
      draggable={false}
      width={Math.round((height * 414) / 181)}
      height={height}
      className={`block max-w-full object-contain ${className}`.trim()}
    />
  );
}

/** Compatibility alias for older call sites; new brand placements use MirraLogo. */
export function MirraWordmark({ className = "" }: { className?: string }) {
  return <MirraLogo className={className} height={34} />;
}
