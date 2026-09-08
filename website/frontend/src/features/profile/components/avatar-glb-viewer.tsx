import { Suspense, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Canvas } from "@react-three/fiber";
import { Bounds, ContactShadows, OrbitControls, useGLTF } from "@react-three/drei";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import { Skeleton } from "@/components/ui/misc";
import { AVATAR_GLB_STALE_KEY } from "../glb-query-keys";

function Model({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  return <primitive object={scene} />;
}

/** Renders one GLB in an orbitable 3D view.
 *
 * The GLB routes need an Authorization header, which a loader given a plain
 * URL cannot send — so the file is fetched through the authed client and
 * handed to the loader as an object URL instead. That trades away the
 * route's HTTP caching: every mount re-downloads. See doc 08, Concern 12.
 */
export function GlbViewer({
  queryKey,
  fetchGlb,
  className = "",
  emptyMessage = "This model isn't available.",
  fallbackImageUrl = null,
  retryLabel,
  onLoadStateChange,
}: {
  queryKey: unknown[];
  fetchGlb: () => Promise<Blob>;
  className?: string;
  emptyMessage?: string;
  fallbackImageUrl?: string | null;
  retryLabel?: string;
  onLoadStateChange?: (state: "loading" | "ready" | "error") => void;
}) {
  const {
    data: blob,
    isLoading,
    isError,
    isFetching,
    refetch,
  } = useQuery({
    queryKey,
    queryFn: fetchGlb,
    staleTime: Infinity,
    retry: false,
  });

  const [url, setUrl] = useState<string | null>(null);
  const [autoRotate, setAutoRotate] = useState(false);

  useEffect(() => {
    if (!blob) return;
    const objectUrl = URL.createObjectURL(blob);
    setUrl(objectUrl);
    return () => {
      URL.revokeObjectURL(objectUrl);
      useGLTF.clear(objectUrl);
      setUrl(null);
    };
  }, [blob]);

  const loadState = isLoading || (blob && !url) ? "loading" : isError || !url ? "error" : "ready";

  useEffect(() => {
    onLoadStateChange?.(loadState);
  }, [loadState, onLoadStateChange]);

  if (loadState === "loading") return <Skeleton className={`w-full rounded-2xl ${className}`} />;

  if (loadState === "error" && !fallbackImageUrl && !retryLabel) {
    return (
      <div
        className={`flex w-full items-center justify-center rounded-2xl border border-line bg-surface ${className}`}
      >
        <p className="px-4 text-center text-xs text-muted">{emptyMessage}</p>
      </div>
    );
  }

  if (loadState === "error") {
    return (
      <div
        className={`relative flex w-full items-center justify-center overflow-hidden rounded-2xl border border-line bg-surface ${className}`}
      >
        {fallbackImageUrl && (
          <img
            src={fallbackImageUrl}
            alt=""
            draggable={false}
            className="absolute inset-0 size-full object-contain p-[4%]"
          />
        )}
        <div
          className={
            fallbackImageUrl
              ? "absolute right-4 bottom-4 left-4 z-10 mx-auto flex w-fit max-w-[calc(100%-2rem)] items-center gap-2 rounded-full border border-white/90 bg-paper/82 px-3 py-2 text-xs text-muted shadow-[0_12px_32px_-22px_rgba(33,31,28,0.62)] backdrop-blur-xl"
              : "relative z-10 flex max-w-xs -translate-y-8 flex-col items-center px-5 text-center"
          }
        >
          {!fallbackImageUrl && (
            <span
              aria-hidden
              className="mb-4 flex size-18 items-center justify-center rounded-full border border-line-strong/70 bg-paper/78 text-ink-soft shadow-[0_18px_44px_-32px_rgba(33,31,28,0.7)]"
            >
              <svg
                width="32"
                height="32"
                viewBox="0 0 32 32"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.35"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="m16 4 9 5v11l-9 5-9-5V9l9-5Z" />
                <path d="m7 9 9 5 9-5M16 14v11" />
              </svg>
            </span>
          )}
          <span className={`min-w-0 leading-5 ${fallbackImageUrl ? "" : "text-sm text-ink-soft"}`}>
            {fallbackImageUrl ? "Showing your saved preview. " : ""}
            {emptyMessage}
          </span>
          {retryLabel && (
            <button
              type="button"
              disabled={isFetching}
              onClick={() => void refetch()}
              className={`${fallbackImageUrl ? "min-h-9" : "mt-4 min-h-10"} shrink-0 rounded-full bg-ink px-3 text-[11px] font-semibold text-canvas disabled:opacity-55`}
            >
              {isFetching ? "Retrying…" : retryLabel}
            </button>
          )}
        </div>
      </div>
    );
  }

  if (!url) return null;

  return (
    <div
      className={`relative w-full overflow-hidden rounded-2xl border border-line bg-gradient-to-b from-surface to-paper ${className}`}
    >
      <Canvas shadows camera={{ fov: 35 }} dpr={[1, 2]}>
        <ambientLight intensity={0.55} />
        <directionalLight position={[4, 8, 5]} intensity={2.2} castShadow />
        <directionalLight position={[-5, 3, -4]} intensity={0.7} />
        <directionalLight position={[0, 2, -6]} intensity={0.9} />

        <Suspense fallback={null}>
          {/* Frames the camera to the model's real bounds, so nothing is clipped. */}
          <Bounds fit clip observe margin={1.15}>
            <Model url={url} />
          </Bounds>
          <ContactShadows position={[0, -0.001, 0]} opacity={0.45} scale={6} blur={2.2} far={4} />
        </Suspense>

        <OrbitControls
          makeDefault
          enablePan={false}
          enableDamping
          dampingFactor={0.08}
          autoRotate={autoRotate}
          autoRotateSpeed={1.2}
          minPolarAngle={0.15}
          maxPolarAngle={Math.PI / 1.9}
        />
      </Canvas>

      <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-center justify-between p-3">
        <span className="mono-tag text-[9px]! tracking-[0.2em]! text-faint">
          DRAG TO ROTATE · SCROLL TO ZOOM
        </span>
        <button
          type="button"
          onClick={() => setAutoRotate((on) => !on)}
          className="pointer-events-auto rounded-full border border-line bg-paper/80 px-3 py-1 text-[11px] text-ink-soft backdrop-blur hover:text-ink"
        >
          {autoRotate ? "Stop" : "Auto-rotate"}
        </button>
      </div>
    </div>
  );
}

/** The shopper's own avatar, with no garment on it. */
export function AvatarGlbViewer({ className = "" }: { className?: string }) {
  const qc = useQueryClient();
  return (
    <GlbViewer
      queryKey={["account", "avatar-glb"]}
      fetchGlb={async () => {
        const result = await getRuntimeProvider().getAvatarGlb();
        // Staleness only arrives as a header on this 66MB response, so it is
        // cached separately rather than costing a second download.
        qc.setQueryData(AVATAR_GLB_STALE_KEY, result.isStale);
        return result.blob;
      }}
      className={className}
      emptyMessage="Your avatar model isn't available."
    />
  );
}
