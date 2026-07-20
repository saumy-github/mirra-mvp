import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import type { CaptureStep } from "@/integrations/mirra-api/types";
import { Button } from "@/components/ui/button";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { PoseSilhouette } from "./silhouettes";

export interface CapturedImage {
  mimeType: string;
  byteSize: number;
  width: number;
  height: number;
}

/**
 * Mobile camera capture for one step: silhouette + lighting/distance
 * guidance, retake, and an always-available file-upload fallback.
 * In demo engine mode only image METADATA leaves the device.
 */
export function CameraCapture({
  step,
  onConfirm,
  onSkip,
  busy,
}: {
  step: CaptureStep;
  onConfirm: (img: CapturedImage) => void;
  onSkip?: () => void;
  busy?: boolean;
}) {
  const reduceMotion = useReducedMotion();
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraState, setCameraState] = useState<"starting" | "live" | "denied">("starting");
  const [preview, setPreview] = useState<{
    url: string;
    img: CapturedImage;
  } | null>(null);

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function start() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: "environment",
            width: { ideal: 1080 },
            height: { ideal: 1920 },
          },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play().catch(() => undefined);
        }
        setCameraState("live");
      } catch {
        setCameraState("denied");
      }
    }
    if (!preview) void start();
    return () => {
      cancelled = true;
      stopStream();
    };
  }, [preview, stopStream]);

  function takePhoto() {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")!.drawImage(video, 0, 0);
    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        setPreview({
          url: URL.createObjectURL(blob),
          img: {
            mimeType: "image/jpeg",
            byteSize: blob.size,
            width: canvas.width,
            height: canvas.height,
          },
        });
        stopStream();
      },
      "image/jpeg",
      0.88,
    );
  }

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const bitmap = await createImageBitmap(file);
      setPreview({
        url: URL.createObjectURL(file),
        img: {
          mimeType: file.type || "image/jpeg",
          byteSize: file.size,
          width: bitmap.width,
          height: bitmap.height,
        },
      });
      bitmap.close();
      stopStream();
    } catch {
      // unreadable file — ignore, user can pick another
    }
  }

  function retake() {
    if (preview) URL.revokeObjectURL(preview.url);
    setPreview(null);
  }

  return (
    <div className="flex w-full flex-col">
      <div className="relative mx-auto aspect-3/4 w-full max-w-sm overflow-hidden rounded-[28px] bg-ink shadow-[0_28px_64px_-34px_rgba(0,0,0,0.65)]">
        <AnimatePresence mode="wait" initial={false}>
          {preview ? (
            <motion.img
              key="preview"
              src={preview.url}
              alt="Your captured photograph, ready to confirm"
              className="h-full w-full object-cover"
              initial={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 1.03 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={
                reduceMotion
                  ? { duration: 0.14 }
                  : { type: "spring", stiffness: 280, damping: 30, mass: 0.9 }
              }
            />
          ) : cameraState === "denied" ? (
            <motion.div
              key="denied"
              className="flex h-full flex-col items-center justify-center px-8 text-center text-white/80"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <span
                className="flex size-14 items-center justify-center rounded-full bg-white/10 text-2xl"
                aria-hidden
              >
                ◌
              </span>
              <p className="mt-5 text-base font-semibold text-white">Camera unavailable</p>
              <p className="mt-2 text-sm leading-relaxed text-white/60">
                Allow access in your browser settings, or choose an existing photograph below.
              </p>
            </motion.div>
          ) : (
            <motion.div
              key="camera"
              className="h-full w-full"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <video ref={videoRef} playsInline muted className="h-full w-full object-cover" />
              <PoseSilhouette
                pose={step.silhouette}
                className="pointer-events-none absolute inset-0 m-auto h-[90%]"
              />
              <div className="absolute inset-x-0 top-0 bg-linear-to-b from-black/65 via-black/24 to-transparent px-5 pt-5 pb-14 text-center">
                <p className="text-[17px] font-semibold tracking-[-0.02em] text-white">
                  {step.title}
                </p>
                <p className="mt-1.5 text-[13px] leading-relaxed text-white/76">{step.guidance}</p>
              </div>
              <div className="absolute inset-x-4 bottom-4 flex items-center justify-center gap-2 rounded-full bg-black/24 px-3 py-2 text-center backdrop-blur-md">
                <span className="size-1.5 rounded-full bg-white/80" />
                <p className="text-[11px] font-medium text-white/80">
                  Full body · 2–3 m away · even light
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {preview && (
          <div className="glass absolute top-4 left-4 rounded-full px-3 py-1.5 text-[11px] font-semibold text-ink-soft">
            Ready to use
          </div>
        )}
      </div>

      <div className="mx-auto mt-5 flex w-full max-w-sm flex-col gap-2.5">
        {preview ? (
          <>
            <Button size="lg" onClick={() => onConfirm(preview.img)} loading={busy}>
              Use this photo
            </Button>
            <Button variant="outline" size="lg" onClick={retake} disabled={busy}>
              Retake
            </Button>
          </>
        ) : (
          <>
            {cameraState === "live" && (
              <motion.button
                type="button"
                onClick={takePhoto}
                aria-label="Take photo"
                className="mx-auto flex size-17 items-center justify-center rounded-full border-[5px] border-paper bg-white/35 shadow-[0_5px_18px_rgba(0,0,0,0.22)]"
                whileTap={{ scale: 0.92 }}
                transition={{
                  type: "spring",
                  stiffness: 560,
                  damping: 30,
                  mass: 0.55,
                }}
              >
                <span className="size-11.5 rounded-full bg-paper shadow-[0_1px_0_rgba(255,255,255,0.8)_inset]" />
              </motion.button>
            )}
            <label className="pressable flex h-11 cursor-pointer items-center justify-center rounded-[14px] border border-line-strong bg-paper text-sm font-medium text-ink hover:border-ink/50">
              Upload from library instead
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,image/heic"
                className="sr-only"
                onChange={onFile}
              />
            </label>
            {onSkip && !step.required && (
              <button
                type="button"
                onClick={onSkip}
                className="py-1 text-sm text-muted hover:text-ink"
              >
                Skip this view
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
