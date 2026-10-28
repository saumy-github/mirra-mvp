import { useCallback, useEffect, useRef, useState } from "react";
import { Camera, Check, RefreshCw, SwitchCamera, Timer, X } from "lucide-react";
import {
  cameraError,
  CameraSession,
  captureCameraFrame,
  type CameraFacing,
} from "./camera-session";
import "./live-camera.css";
import { usePhotoPreview } from "./use-photo-preview";

export function LiveCamera({
  label,
  hint,
  guide,
  facing: initialFacing = "environment",
  onConfirm,
  onCancel,
}: {
  label: string;
  hint: string;
  guide?: string;
  facing?: CameraFacing;
  onConfirm: (photo: File) => void;
  onCancel?: () => void;
}) {
  const video = useRef<HTMLVideoElement>(null);
  const session = useRef(new CameraSession());
  const mounted = useRef(true);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const [status, setStatus] = useState<"idle" | "opening" | "live" | "paused">("idle");
  const [facing, setFacing] = useState(initialFacing);
  const [error, setError] = useState<string | null>(null);
  const [photo, setPhoto] = useState<File | null>(null);
  const [capturing, setCapturing] = useState(false);
  const [timerOn, setTimerOn] = useState(initialFacing !== "user");
  const [countdown, setCountdown] = useState<number | null>(null);
  const preview = usePhotoPreview(photo);

  const stopTimer = useCallback(() => {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
    setCountdown(null);
  }, []);

  useEffect(() => {
    mounted.current = true;
    const camera = session.current;
    function pause() {
      if (document.visibilityState !== "hidden") return;
      camera.stop();
      stopTimer();
      setStatus("paused");
    }
    document.addEventListener("visibilitychange", pause);
    return () => {
      mounted.current = false;
      camera.stop();
      if (timer.current) clearInterval(timer.current);
      document.removeEventListener("visibilitychange", pause);
    };
  }, [stopTimer]);

  async function open(nextFacing = facing) {
    stopTimer();
    setPhoto(null);
    setError(null);
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setError(
        "Live camera needs a secure connection. Open Mirra over HTTPS, or use localhost on this computer.",
      );
      return;
    }
    setStatus("opening");
    let openedStream: MediaStream | null = null;
    try {
      const stream = await session.current.open(navigator.mediaDevices, nextFacing);
      if (!stream || !mounted.current || !video.current) return;
      openedStream = stream;
      video.current.srcObject = stream;
      await video.current.play();
      if (mounted.current && session.current.isActive(stream)) setStatus("live");
    } catch (reason) {
      if (!mounted.current || (openedStream && !session.current.isActive(openedStream))) return;
      session.current.stop();
      if (mounted.current) {
        setError(cameraError(reason));
        setStatus("idle");
      }
    }
  }

  async function takePhoto() {
    if (!video.current) return;
    setCapturing(true);
    setError(null);
    try {
      const frame = await captureCameraFrame(
        video.current,
        label.toLowerCase().replace(/\W+/g, "-"),
      );
      if (!mounted.current) return;
      setPhoto(frame);
      session.current.stop();
      setStatus("idle");
    } catch (reason) {
      if (mounted.current) setError(reason instanceof Error ? reason.message : "Please try again.");
    } finally {
      if (mounted.current) setCapturing(false);
    }
  }

  function shutter() {
    if (!timerOn) {
      void takePhoto();
      return;
    }
    let remaining = 5;
    setCountdown(remaining);
    timer.current = setInterval(() => {
      remaining -= 1;
      if (remaining === 0) {
        stopTimer();
        void takePhoto();
      } else setCountdown(remaining);
    }, 1000);
  }

  return (
    <section className="live-camera" aria-label={`${label} camera`}>
      <div className="live-camera-view" data-active={status === "live"}>
        <video
          ref={video}
          muted
          playsInline
          autoPlay
          className={facing === "user" ? "camera-mirrored" : ""}
          hidden={!!photo || status === "idle" || status === "paused"}
          aria-label="Live camera preview"
        />
        {preview ? (
          <img
            src={preview}
            alt={`Review your ${label.toLowerCase()} photo`}
            className="camera-result"
          />
        ) : (
          status !== "live" && (
            <div className="camera-welcome">
              {guide && <img src={guide} alt="" />}
              <span>
                {status === "opening"
                  ? "Allow camera access to continue"
                  : status === "paused"
                    ? "Your camera is paused"
                    : "Let’s get you in the frame"}
              </span>
              <p>{hint}</p>
            </div>
          )
        )}
        {status === "live" && (
          <span className="camera-live-label">
            <span /> Live camera
          </span>
        )}
        {countdown !== null && (
          <span className="camera-countdown" role="status" aria-live="assertive">
            {countdown}
          </span>
        )}
      </div>
      {error && (
        <p className="camera-error" role="alert">
          {error}
        </p>
      )}
      {photo ? (
        <>
          <p className="camera-hint">Check that you’re clearly visible and the photo is sharp.</p>
          <div className="camera-controls">
            <button type="button" className="camera-secondary" onClick={() => void open()}>
              <RefreshCw size={16} /> Retake
            </button>
            <button type="button" className="camera-primary" onClick={() => onConfirm(photo)}>
              Use photo <Check size={16} />
            </button>
          </div>
        </>
      ) : status === "live" ? (
        <>
          <p className="camera-hint">{hint}</p>
          <div className="camera-controls">
            <button
              type="button"
              className="camera-tool"
              aria-label={timerOn ? "Turn off five-second timer" : "Turn on five-second timer"}
              aria-pressed={timerOn}
              disabled={countdown !== null || capturing}
              onClick={() => setTimerOn(!timerOn)}
            >
              <Timer size={19} />
              <span>{timerOn ? "5s" : "Off"}</span>
            </button>
            <button
              type="button"
              className="camera-shutter"
              aria-label={
                countdown !== null ? "Cancel countdown" : `Take ${label.toLowerCase()} photo`
              }
              disabled={capturing}
              onClick={countdown !== null ? stopTimer : shutter}
            >
              {countdown !== null ? <X size={24} /> : <Camera size={24} />}
            </button>
            <button
              type="button"
              className="camera-tool"
              aria-label="Switch camera"
              disabled={countdown !== null || capturing}
              onClick={() => {
                const next = facing === "user" ? "environment" : "user";
                setFacing(next);
                void open(next);
              }}
            >
              <SwitchCamera size={21} />
              <span>Flip</span>
            </button>
          </div>
        </>
      ) : (
        <button
          type="button"
          className="camera-primary camera-open"
          disabled={status === "opening"}
          onClick={() => void open()}
        >
          <Camera size={18} />
          {status === "opening"
            ? "Waiting for permission…"
            : status === "paused"
              ? "Resume camera"
              : "Open live camera"}
        </button>
      )}
      {onCancel && (
        <button type="button" className="camera-cancel" onClick={onCancel}>
          Back
        </button>
      )}
    </section>
  );
}
