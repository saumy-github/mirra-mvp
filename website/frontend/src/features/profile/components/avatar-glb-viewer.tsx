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
}: {
  queryKey: unknown[];
  fetchGlb: () => Promise<Blob>;
  className?: string;
  emptyMessage?: string;
}) {
  const { data: blob, isLoading, isError } = useQuery({
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

  if (isLoading || (blob && !url)) return <Skeleton className={`w-full rounded-2xl ${className}`} />;

  if (isError || !url) {
    return (
      <div
        className={`flex w-full items-center justify-center rounded-2xl border border-line bg-surface ${className}`}
      >
        <p className="px-4 text-center text-xs text-muted">{emptyMessage}</p>
      </div>
    );
  }

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
        <span className="mono-tag text-[9px]! tracking-[0.2em]! text-faint">DRAG TO ROTATE · SCROLL TO ZOOM</span>
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
