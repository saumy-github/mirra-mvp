import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import type { FacePhotosInput } from "@/integrations/mirra-api/types";
import { FACE_GLB_KEY } from "../glb-query-keys";
import { PhotoInput } from "./photo-measurement";

const POLL_MS = 1500;

/**
 * Face photos: front (required) and the head turned ~45° each way (optional,
 * they fill in the sides). Shared by the desktop panel below and the phone
 * page reached through the QR code, which submits through the pairing link.
 */
export function FaceCaptureForm<T>({
  submit,
  onStarted,
  submitLabel = "Add my face",
  compact = false,
}: {
  submit: (input: FacePhotosInput) => Promise<T>;
  onStarted: (result: T) => void;
  submitLabel?: string;
  compact?: boolean;
}) {
  const [showSides, setShowSides] = useState(!compact);
  const [front, setFront] = useState<File | null>(null);
  const [left, setLeft] = useState<File | null>(null);
  const [right, setRight] = useState<File | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const start = useMutation({
    mutationFn: () => submit({ front: front!, left, right }),
    onSuccess: onStarted,
  });

  return (
    <div>
      <ul
        hidden={compact}
        className="space-y-1.5 rounded-2xl border border-line bg-paper/70 px-5 py-4 text-[13px] text-ink-soft"
      >
        <li>• Arm's length away, phone at eye level, soft even light (face a window).</li>
        <li>• Relaxed face, lips together, hair off your face, no glasses.</li>
        <li>
          • <strong>Front</strong> is enough; the two turned photos (about 45° each way) improve the
          sides.
        </li>
        <li>• Photos are deleted once your face is built. You can remove your face any time.</li>
      </ul>
      <div className={`mt-5 grid gap-4 ${showSides ? "sm:grid-cols-3" : ""}`}>
        <PhotoInput
          label="Front"
          file={front}
          onChange={setFront}
          onError={setLocalError}
          facing="user"
        />
        {showSides && (
          <PhotoInput
            label="Turned left (optional)"
            facing="user"
            file={left}
            onChange={setLeft}
            onError={setLocalError}
          />
        )}
        {showSides && (
          <PhotoInput
            label="Turned right (optional)"
            facing="user"
            file={right}
            onChange={setRight}
            onError={setLocalError}
          />
        )}
      </div>
      {!showSides && (
        <button type="button" className="setup-text-button" onClick={() => setShowSides(true)}>
          Add side views (optional)
        </button>
      )}
      {(localError || start.error) && (
        <p role="alert" className="mt-4 rounded-xl bg-error/8 px-4 py-3 text-sm text-error">
          {localError ??
            (start.error instanceof Error
              ? start.error.message
              : "Upload didn't complete — please retry.")}
        </p>
      )}
      <Button
        type="button"
        size="lg"
        className="mt-6 w-full"
        loading={start.isPending}
        onClick={() => (front ? start.mutate() : setLocalError("Add a front photo of your face."))}
      >
        {submitLabel}
      </Button>
    </div>
  );
}

/**
 * "Your face" on the avatar page: status of the latest face, add/replace it
 * from this device, or remove it. The 3D viewer picks the face up through
 * FACE_GLB_KEY once it is ready.
 */
export function FacePanel() {
  const qc = useQueryClient();
  const [adding, setAdding] = useState(false);
  const latest = useQuery({
    queryKey: ["account", "face"],
    queryFn: () => getRuntimeProvider().getLatestFace(),
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      if (state === "queued" || state === "processing") return POLL_MS;
      return false;
    },
  });
  const face = latest.data;
  const busy = face?.state === "queued" || face?.state === "processing";

  // When a face finishes building, the viewer's cached face GLB is out of date.
  const previousState = useRef(face?.state);
  useEffect(() => {
    const before = previousState.current;
    previousState.current = face?.state;
    if ((before === "queued" || before === "processing") && face?.state === "ready") {
      void qc.invalidateQueries({ queryKey: FACE_GLB_KEY });
    }
  }, [face?.state, qc]);

  const remove = useMutation({
    mutationFn: () => getRuntimeProvider().deleteFace(),
    onSuccess: () => {
      qc.setQueryData(["account", "face"], null);
      qc.setQueryData(FACE_GLB_KEY, null);
    },
  });

  return (
    <section className="profile-panel mt-6 p-5" aria-labelledby="face-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="face-title" className="text-base font-semibold text-ink">
            Your face
          </h2>
          <p className="mt-1 text-[13px] text-muted">
            {busy
              ? face!.stageLabel
              : face?.state === "ready"
                ? "Your face is on your avatar, in the studio too."
                : face?.state === "failed"
                  ? face.failureReason
                  : "Add a photo of your face so your avatar looks like you."}
          </p>
          {face?.state === "ready" && face.warnings.length > 0 && (
            <p className="mt-1 text-xs text-muted">{face.warnings.join(" ")}</p>
          )}
        </div>
        <div className="flex gap-2">
          {face?.state === "ready" && (
            <Button
              size="sm"
              variant="ghost"
              loading={remove.isPending}
              onClick={() => remove.mutate()}
            >
              Remove
            </Button>
          )}
          {!busy && !adding && (
            <Button size="sm" variant="outline" onClick={() => setAdding(true)}>
              {face?.state === "ready" ? "Replace" : "Add your face"}
            </Button>
          )}
        </div>
      </div>
      {adding && (
        <div className="mt-5">
          <FaceCaptureForm
            submit={(input) => getRuntimeProvider().startFace(input)}
            onStarted={(started) => {
              qc.setQueryData(["account", "face"], started);
              setAdding(false);
            }}
          />
        </div>
      )}
    </section>
  );
}
