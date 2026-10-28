import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, LoaderCircle, LockKeyhole, QrCode } from "lucide-react";
import { MirraMark } from "@/components/ui/logo";
import { BodyCameraWizard, FaceCameraWizard } from "@/features/onboarding/phone-capture";
import { getRuntimeProvider, MirraApiError } from "@/integrations/mirra-api";
import { useAccount } from "@/hooks/use-shopper";
import "@/features/onboarding/setup.css";

const api = getRuntimeProvider();

/** Public, token-scoped handoff. A camera frame is sent through the existing
 * photo/face APIs; this route never exposes private measurement results. */
export default function CaptureLink() {
  const { token = "" } = useParams<{ token: string }>();
  const qc = useQueryClient();
  const [retake, setRetake] = useState(false);
  const [faceRetake, setFaceRetake] = useState(false);
  const marked = useRef(false);
  const linkKey = ["capture-link", token];
  const link = useQuery({
    queryKey: linkKey,
    queryFn: () => api.getCaptureLink(token),
    retry: false,
  });
  const progress = useQuery({
    queryKey: ["capture-link-progress", token],
    queryFn: () => api.getCaptureLinkProgress(token),
    enabled: !!link.data?.captureId,
    refetchInterval: (q) =>
      ["ready", "failed", "applied"].includes(q.state.data?.state ?? "") ? false : 2000,
  });
  const face = useQuery({
    queryKey: ["capture-link-face", token],
    queryFn: () => api.getCaptureLinkFace(token),
    enabled: !!link.data?.faceId,
    refetchInterval: (q) =>
      ["ready", "failed"].includes(q.state.data?.state ?? "") ? false : 2000,
  });
  useEffect(() => {
    if (!link.data || link.data.complete || marked.current) return;
    marked.current = true;
    void api.setCaptureStage(token, "capturing").catch(() => {
      marked.current = false;
    });
  }, [link.data, token]);
  const finish = useMutation({
    mutationFn: (skip: boolean) => api.finishCapture(token, skip),
    onSuccess: () => {
      setFaceRetake(false);
      void qc.invalidateQueries({ queryKey: linkKey });
    },
  });
  // A phone opened from the QR code has no session. Only a browser that is
  // already signed in (the "use this device" case) can continue setup here.
  const { data: signedIn } = useAccount();
  const linkGone =
    link.error instanceof MirraApiError && (link.error.status === 404 || link.error.status === 410);
  const bodyDone = !!link.data?.captureId || link.data?.measurementMethod === "manual";
  const faceDone = !!link.data?.faceId;
  const done = link.data?.complete && !faceRetake;
  const bodyFailed = progress.data?.state === "failed";
  async function uploading<T>(send: () => Promise<T>) {
    await api.setCaptureStage(token, "uploading");
    try {
      return await send();
    } catch (error) {
      await api.setCaptureStage(token, "capturing").catch(() => {});
      throw error;
    }
  }

  return (
    <div className="mirra-setup">
      <main className="setup-phone">
        <header className="setup-phone-header">
          <span className="setup-brand">
            <MirraMark size={25} />
            <span>MIRRA</span>
          </span>
          <span className="phone-private">
            <LockKeyhole size={12} strokeWidth={1.5} /> Private capture
          </span>
        </header>
        {link.isLoading ? (
          <div className="setup-phone-done" role="status">
            <LoaderCircle className="setup-spinner" size={24} />
            <p>Opening your camera guide…</p>
          </div>
        ) : link.error && linkGone ? (
          <section className="setup-phone-done">
            <span className="phone-success phone-success--muted">
              <QrCode size={40} strokeWidth={1.25} />
            </span>
            <h1>This code has expired.</h1>
            <p role="alert">
              Look at your computer. A fresh code is waiting on the setup screen. Scan that one
              to carry on. Anything you already sent is kept.
            </p>
            {signedIn && (
              <Link className="setup-primary" to="/onboarding/qr">
                Open setup on this device <ArrowRight size={16} />
              </Link>
            )}
          </section>
        ) : link.error ? (
          <section className="setup-phone-done">
            <h1>Let’s reconnect.</h1>
            <p role="alert">
              We couldn’t reach Mirra. Check your connection, then try again. Your progress is
              saved.
            </p>
            <button className="setup-primary" onClick={() => void link.refetch()}>
              Try again
            </button>
          </section>
        ) : done ? (
          <section className="setup-phone-done setup-enter">
            <span className="phone-success">
              <CheckCircle2 size={46} strokeWidth={1.25} />
            </span>
            <h1>All sent. Thank you.</h1>
            <p>You can put your phone down. We’ll take it from here on your computer.</p>
            {bodyFailed && (
              <p className="camera-error" role="alert">
                {progress.data?.failureReason} Return to your computer to start a new capture.
              </p>
            )}
            {face.data?.state === "failed" && (
              <>
                <p className="camera-error" role="alert">
                  {face.data.failureReason}
                </p>
                <button className="setup-primary" onClick={() => setFaceRetake(true)}>
                  Retake face photo
                </button>
              </>
            )}
            {signedIn && (
              <Link className="setup-text-button" to="/onboarding/qr">
                Continue setup on this device <ArrowRight size={14} />
              </Link>
            )}
          </section>
        ) : (
          <>
            {!bodyDone || retake ? (
              <BodyCameraWizard
                initial={{
                  gender: link.data?.gender ?? "male",
                  heightCm: link.data?.heightCm,
                  weightKg: link.data?.weightKg,
                }}
                submit={(input) => uploading(() => api.uploadViaCaptureLink(token, input))}
                onStarted={(capture) => {
                  qc.setQueryData(["capture-link-progress", token], capture);
                  setRetake(false);
                  void api.setCaptureStage(token, "capturing").catch(() => {});
                  void qc.invalidateQueries({ queryKey: linkKey });
                }}
              />
            ) : bodyFailed ? (
              <section className="setup-phone-done">
                <h1>Let’s try those again.</h1>
                <p className="camera-error" role="alert">
                  {progress.data?.failureReason}
                </p>
                <button className="setup-primary" onClick={() => setRetake(true)}>
                  Retake body photos
                </button>
              </section>
            ) : !faceDone || faceRetake ? (
              <FaceCameraWizard
                submit={(input) => uploading(() => api.uploadFaceViaCaptureLink(token, input))}
                onStarted={(capture) => {
                  qc.setQueryData(["capture-link-face", token], capture);
                  void qc.invalidateQueries({ queryKey: linkKey });
                  finish.mutate(false);
                }}
                onSkip={() => finish.mutate(true)}
                skipPending={finish.isPending}
              />
            ) : (
              <section className="setup-phone-done">
                <span className="phone-success">
                  <CheckCircle2 size={40} strokeWidth={1.3} />
                </span>
                <h1>Your photos are here.</h1>
                <p>
                  {face.data?.state === "failed"
                    ? face.data.failureReason
                    : "One last step, then you can return to your computer."}
                </p>
                <button
                  className="setup-primary"
                  disabled={finish.isPending}
                  onClick={() => finish.mutate(face.data?.state === "failed")}
                >
                  {finish.isPending ? "Finishing…" : "Finish & return to your computer"}{" "}
                  <ArrowRight size={16} />
                </button>
                <button
                  className="setup-text-button"
                  disabled={finish.isPending}
                  onClick={() => setFaceRetake(true)}
                >
                  Retake face photo
                </button>
              </section>
            )}
            {finish.error && (
              <p className="camera-error" role="alert">
                {finish.error.message}
                <button
                  className="setup-text-button"
                  onClick={() => finish.mutate(finish.variables ?? false)}
                >
                  Try again
                </button>
              </p>
            )}
          </>
        )}
        <p className="phone-privacy">
          Photos are taken live and deleted after processing. Your measurements and avatar stay in
          your account.
        </p>
      </main>
    </div>
  );
}
