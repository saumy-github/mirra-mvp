import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  ArrowUpRight,
  Camera,
  Check,
  CheckCircle2,
  ChevronDown,
  Copy,
  LoaderCircle,
  LogOut,
  Play,
  RefreshCw,
  Ruler,
  Smartphone,
  UserRound,
} from "lucide-react";
import QRCode from "qrcode";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  getRuntimeProvider,
  type AvatarSetup,
  type PhotoMeasurementField,
} from "@/integrations/mirra-api";
import { useAccount, useAuthMutations, useAvatarProfile } from "@/hooks/use-shopper";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { MirraMark } from "@/components/ui/logo";
import { AvatarGlbViewer } from "@/features/profile/components/avatar-glb-viewer";
import { MeasurementForm } from "@/features/profile/components/measurement-form";
import { FACE_GLB_KEY } from "@/features/profile/glb-query-keys";
import { onboardingStudioDestination } from "@/lib/post-auth";
import {
  captureUrl,
  PHONE_QUIET_MS,
  rememberCaptureLink,
  setupStep,
  storedCaptureLink,
} from "./setup-utils";
import { onboardingPreviewEnabled, previewSetupUrl } from "./preview-config";
import { MeasurementSliders } from "./measurement-sliders";
import { useMeasurementReview } from "./use-measurement-review";
import "./setup.css";

const api = getRuntimeProvider();

export function SetupFlow() {
  const {
    data: account,
    isLoading: accountLoading,
    error: accountError,
    refetch: reloadAccount,
  } = useAccount();
  const {
    data: avatar,
    isLoading: avatarLoading,
    error: avatarError,
    refetch: reloadAvatar,
  } = useAvatarProfile(!!account);
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const destination = onboardingStudioDestination(params.get("next"));
  const qc = useQueryClient();
  const key = ["account", "avatar-setup", account?.shopperId];
  const [manual, setManual] = useState(false);
  const [tourDone, setTourDone] = useState(false);
  const [syncShown, setSyncShown] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showNewCode, setShowNewCode] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const [repairFace, setRepairFace] = useState(false);
  const [clock, setClock] = useState(Date.now());
  const latest = useQuery({
    queryKey: key,
    queryFn: () => api.getLatestAvatarSetup(),
    enabled: !!account,
    refetchInterval: (q) => (q.state.data?.state === "complete" ? false : 2000),
    retry: 1,
  });
  const setup = latest.data;
  const initialStarted = useRef(false);
  const create = useMutation({
    mutationFn: async (method: "photos" | "manual") => {
      const pairing = await api.createPhotoPairing(true, method);
      rememberCaptureLink(pairing.pairingId, pairing);
      qc.setQueryData(["capture-qr", pairing.pairingId], pairing);
      return api.getAvatarSetup(pairing.pairingId);
    },
    onSuccess: (s) => {
      qc.setQueryData(key, s);
      setManual(false);
      setTourDone(false);
      setSyncShown(false);
    },
  });
  const { mutate: startSetup } = create;
  useEffect(() => {
    if (!accountLoading && !accountError && !account) {
      navigate(`/auth/sign-up?next=${encodeURIComponent("/onboarding/qr")}`, { replace: true });
    }
  }, [account, accountLoading, accountError, navigate]);
  useEffect(() => {
    if (!account || !latest.isSuccess || avatarLoading || avatarError) return;
    if (
      (!setup && avatar?.version) ||
      (setup?.state === "complete" && (avatar?.version || setup.job?.state === "ready"))
    ) {
      navigate(destination, { replace: true });
      return;
    }
    if ((!setup || setup.state === "complete") && !initialStarted.current) {
      initialStarted.current = true;
      startSetup("photos");
    }
  }, [
    account,
    avatar?.version,
    avatarLoading,
    avatarError,
    latest.isSuccess,
    setup,
    destination,
    navigate,
    startSetup,
  ]);

  const pairingId = setup?.pairing.pairingId;
  const qr = useQuery({
    queryKey: ["capture-qr", pairingId],
    // Reuse the issued code: asking the server again would invalidate a code
    // the phone may already have scanned.
    queryFn: async () => {
      const stored = storedCaptureLink(pairingId!);
      if (stored) return stored;
      const pairing = await api.refreshCaptureLink(pairingId!);
      rememberCaptureLink(pairingId!, pairing);
      return pairing;
    },
    enabled: !!pairingId && (setup?.state === "waiting" || showNewCode || repairFace),
    staleTime: Infinity,
    retry: false,
  });
  const link = qr.data?.token
    ? captureUrl(qr.data.token, window.location.origin, import.meta.env.VITE_CAPTURE_ORIGIN)
    : null;
  const qrImage = useQuery({
    queryKey: ["capture-qr-image", link],
    queryFn: () =>
      QRCode.toDataURL(link!, {
        width: 240,
        margin: 2,
        color: { dark: "#191917", light: "#ffffff" },
      }),
    enabled: !!link,
    staleTime: Infinity,
  });
  useEffect(() => {
    const id = window.setInterval(() => setClock(Date.now()), 15000);
    return () => clearInterval(id);
  }, []);
  const expired = !!qr.data && Date.parse(qr.data.expiresAt) <= clock;
  const localLink = !!link && ["localhost", "127.0.0.1", "[::1]"].includes(new URL(link).hostname);
  const captureFinished = setup?.pairing.captureComplete;
  // The phone reports each step it reaches. A long silence usually means the
  // page was closed or the camera was refused, so offer a way back in.
  const phoneStage = `${setup?.state}:${setup?.pairing.phoneStage}`;
  const [phoneStageSince, setPhoneStageSince] = useState(() => Date.now());
  useEffect(() => setPhoneStageSince(Date.now()), [phoneStage]);
  const phoneQuiet = setup?.state === "capturing" && clock - phoneStageSince > PHONE_QUIET_MS;
  function showCodeAgain() {
    setShowNewCode(true);
    if (!qr.data || expired) void qr.refetch();
  }
  useEffect(() => {
    if (!pairingId) return;
    if (sessionStorage.getItem(`mirra-tour-${pairingId}`) === "seen") {
      setTourDone(true);
      setSyncShown(true);
    }
  }, [pairingId]);
  useEffect(() => {
    if (setup?.face && setup.face.state !== "failed") setRepairFace(false);
  }, [setup?.face]);
  function finishTour() {
    if (pairingId) sessionStorage.setItem(`mirra-tour-${pairingId}`, "seen");
    setTourDone(true);
  }
  useEffect(() => {
    if (!captureFinished || syncShown) return;
    const id = window.setTimeout(() => setSyncShown(true), 1600);
    return () => clearTimeout(id);
  }, [captureFinished, syncShown]);

  const update = useMutation({
    mutationFn: (skipFace: boolean) => api.retryAvatarSetup(pairingId!, skipFace),
    onSuccess: (s) => qc.setQueryData(key, s),
  });
  const review = useMutation({
    mutationFn: (values: Partial<Record<PhotoMeasurementField, number>>) =>
      api.reviewAvatarSetup(pairingId!, values),
    onSuccess: async (s) => {
      qc.setQueryData(key, s);
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["account", "avatar-profile"] }),
        qc.invalidateQueries({ queryKey: ["account", "avatar-glb"], exact: true }),
        qc.invalidateQueries({ queryKey: FACE_GLB_KEY }),
      ]);
      if (s.state === "complete") navigate(destination, { replace: true });
    },
  });
  useEffect(() => {
    if (setup?.state !== "review" && setup?.state !== "complete") return;
    void qc.invalidateQueries({ queryKey: ["account", "avatar-glb"], exact: true });
    void qc.invalidateQueries({ queryKey: FACE_GLB_KEY });
    void qc.invalidateQueries({ queryKey: ["account", "avatar-profile"] });
  }, [setup?.state, qc]);

  async function copy() {
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setCopyError(false);
    } catch {
      setCopyError(true);
    }
  }
  const state = setup?.state ?? "waiting";
  const stage = setupStep(state);
  const isCapture = ["waiting", "capturing", "syncing"].includes(state);
  const error = accountError || avatarError || latest.error || create.error;
  const canChooseMethod =
    !!setup && setup.pairing.measurementMethod !== "manual" && !setup.capture && !repairFace;
  const faceFailed = setup?.face?.state === "failed" && !setup.pairing.faceSkipped;

  return (
    <div className="mirra-setup">
      <header className="setup-topbar">
        <Link to="/" className="setup-brand" aria-label="Mirra home">
          <MirraMark size={28} />
          <span>MIRRA</span>
        </Link>
        <ol className="setup-steps" aria-label="Avatar setup progress">
          {["Photos", "Your avatar", "Review"].map((label, i) => (
            <li
              key={label}
              aria-current={stage === i + 1 ? "step" : undefined}
              data-done={stage > i + 1}
            >
              <span>{stage > i + 1 ? <Check size={13} /> : i + 1}</span>
              <b>{label}</b>
            </li>
          ))}
        </ol>
        <div className="setup-exit">
          <Link className="setup-exit-link" to={destination} title="Your progress is saved">
            Save &amp; exit
          </Link>
          {account && <SetupAccountMenu name={account.displayName} isGuest={account.isGuest} />}
        </div>
      </header>
      <main className="setup-main">
        {error ? (
          <div className="setup-problem">
            <h1>Let’s reconnect.</h1>
            <p role="alert">
              {error instanceof Error ? error.message : "We couldn't load your setup."}
            </p>
            <button
              className="setup-primary"
              onClick={() => {
                if (create.error) create.mutate("photos");
                else {
                  if (accountError) void reloadAccount();
                  if (avatarError) void reloadAvatar();
                  void latest.refetch();
                }
              }}
            >
              Try again <ArrowRight size={16} />
            </button>
          </div>
        ) : accountLoading || latest.isLoading || !setup ? (
          <div className="setup-centered" role="status">
            <LoaderCircle className="setup-spinner" size={26} />
            <p>Preparing your space…</p>
          </div>
        ) : manual ? (
          <section className="setup-manual setup-enter">
            <button className="setup-text-button" onClick={() => setManual(false)}>
              ← Back to photos
            </button>
            <h1>A few details about you.</h1>
            <p>Use measurements you know. You can review them before entering Studio.</p>
            <MeasurementForm
              saveLabel="Continue to face photo"
              onSaved={() => create.mutate("manual")}
            />
          </section>
        ) : state === "failed" && !repairFace ? (
          <div className="setup-problem setup-enter">
            <p className="setup-eyebrow">Your progress is saved</p>
            <h1>A small pause.</h1>
            <p role="alert">{setup.failureReason}</p>
            <div className="setup-action-row">
              {setup.capture?.state === "failed" ? (
                <button
                  className="setup-primary"
                  onClick={() => create.mutate("photos")}
                  disabled={create.isPending}
                >
                  Retake photos <ArrowRight size={16} />
                </button>
              ) : (
                <button
                  className="setup-primary"
                  onClick={() => update.mutate(!!faceFailed)}
                  disabled={update.isPending}
                >
                  {faceFailed ? "Continue without a face" : "Retry avatar build"}
                  <ArrowRight size={16} />
                </button>
              )}
              {faceFailed && (
                <button
                  className="setup-text-button"
                  onClick={() => {
                    setRepairFace(true);
                    setShowNewCode(true);
                    void qr.refetch();
                  }}
                >
                  Retake face photo
                </button>
              )}
            </div>
            {update.error && <p role="alert">{update.error.message}</p>}
            <p className="setup-small">Your account and saved measurements are safe.</p>
          </div>
        ) : isCapture || repairFace ? (
          <div className="setup-enter">
            <header className="setup-heading">
              <h1>Create your avatar</h1>
              <p>
                {setup.pairing.measurementMethod === "manual"
                  ? "Your measurements are saved. Add a face photo to make it yours."
                  : "Take a few live photos on your phone. We’ll build your 3D avatar from them."}
              </p>
            </header>
            <div className="setup-capture-grid">
              <section className="setup-qr-panel" aria-label="Connect your phone">
                <div className="setup-qr-space" aria-live="polite">
                  {state === "syncing" && !showNewCode ? (
                    <>
                      <LoaderCircle className="setup-spinner" size={36} />
                      <p>Syncing your photos…</p>
                      <small>Keep this tab open on your phone.</small>
                    </>
                  ) : state === "capturing" && !showNewCode ? (
                    phoneQuiet ? (
                      <>
                        <Smartphone size={38} strokeWidth={1.2} />
                        <p>Still there?</p>
                        <small>
                          We haven’t heard from your phone in a while. If the page closed, scan the
                          code again. Your photos so far are kept.
                        </small>
                        <button
                          className="setup-primary setup-primary--small"
                          onClick={showCodeAgain}
                        >
                          Show the code again
                        </button>
                      </>
                    ) : (
                      <>
                        <Smartphone size={38} strokeWidth={1.2} />
                        <p>Your phone is connected.</p>
                        <small>Follow the steps there. We’ll take it from here.</small>
                      </>
                    )
                  ) : expired ? (
                    <>
                      <RefreshCw size={30} strokeWidth={1.3} />
                      <p>Let’s get a fresh code.</p>
                      <button className="setup-text-button" onClick={() => void qr.refetch()}>
                        Refresh QR code
                      </button>
                    </>
                  ) : qr.isError || qrImage.isError ? (
                    <>
                      <p role="alert">The code couldn’t load.</p>
                      <button
                        className="setup-text-button"
                        onClick={() => {
                          void qr.refetch();
                          void qrImage.refetch();
                        }}
                      >
                        Try again
                      </button>
                    </>
                  ) : qrImage.data ? (
                    <img
                      src={qrImage.data}
                      width={196}
                      height={196}
                      alt="Scan this QR code with your phone camera to take your photos"
                    />
                  ) : (
                    <LoaderCircle className="setup-spinner" size={28} />
                  )}
                </div>
                <h2>
                  {state === "waiting" || repairFace || showNewCode
                    ? "Scan the QR code"
                    : "Looking good so far"}
                </h2>
                <p>
                  {state === "waiting" || repairFace || showNewCode
                    ? "Open the link on your phone to take photos. We’ll guide you through each one."
                    : "Your photos come back here automatically. There’s nothing to download."}
                </p>
                <div className="setup-action-row">
                  {link && !expired && (
                    <button className="setup-text-button" onClick={() => void copy()}>
                      <Copy size={13} />
                      {copied ? "Link copied" : "Copy phone link"}
                    </button>
                  )}
                  {state !== "waiting" && !showNewCode && !phoneQuiet && (
                    <button className="setup-text-button" onClick={showCodeAgain}>
                      Show the code again
                    </button>
                  )}
                  {showNewCode && state !== "waiting" && (
                    <button className="setup-text-button" onClick={() => setShowNewCode(false)}>
                      Hide code
                    </button>
                  )}
                </div>
                {copyError && (
                  <p role="alert" className="setup-small">
                    Copy isn’t available in this browser. Use the device link above.
                  </p>
                )}
                {link && !expired && (
                  <div className="setup-alternatives" aria-label="Other ways to continue">
                    <span>No phone nearby?</span>
                    <a className="setup-alt-button" href={link} target="_blank" rel="noreferrer">
                      <Camera size={16} strokeWidth={1.5} />
                      Use this device’s camera
                      <ArrowUpRight size={14} />
                    </a>
                    {canChooseMethod && (
                      <button className="setup-alt-button" onClick={() => setManual(true)}>
                        <Ruler size={16} strokeWidth={1.5} />
                        Enter measurements instead
                      </button>
                    )}
                  </div>
                )}
                {localLink && (
                  <p className="setup-local-note">
                    Local preview: use this device. A phone needs the site’s public HTTPS address.
                  </p>
                )}
                <p className="setup-small">Private link · expires in 20 minutes</p>
                {onboardingPreviewEnabled && (
                  <Link
                    className="setup-text-button setup-preview-skip"
                    to={previewSetupUrl(destination)}
                  >
                    Skip for now · preview next steps <ArrowRight size={14} />
                  </Link>
                )}
              </section>
              <figure className="setup-avatar-views">
                <img
                  src="/profile/onboarding-poses.webp"
                  alt="Illustration of an avatar in cream clothing, seen from the front, left, right and back"
                />
                <figcaption>
                  <span>Front</span>
                  <span>Left</span>
                  <span>Right</span>
                  <span>Back</span>
                </figcaption>
                <p>Your avatar, from every angle.</p>
              </figure>
            </div>
            <div className="setup-capture-footer">
              <details>
                <summary>
                  Photo guidelines <ChevronDown size={15} />
                </summary>
                <p>
                  We’ll take a front and side body photo, then an optional face photo. Wear fitted
                  clothing and stand against a plain background, with soft light in front of you.
                  For body photos, ask someone to hold your phone upright at chest height, far
                  enough away to include your feet. Face photos are optional. Raw photos are deleted
                  after processing.
                </p>
              </details>
            </div>
          </div>
        ) : captureFinished && !syncShown && !["updating", "complete"].includes(state) ? (
          <div className="setup-centered setup-enter" role="status">
            <CheckCircle2 className="setup-success-mark" size={60} strokeWidth={1} />
            <h1>All here. Thank you.</h1>
            <p>Your photos are synced. Let’s bring your avatar to life.</p>
          </div>
        ) : !tourDone && state !== "updating" && state !== "complete" ? (
          <SetupTour ready={state === "review"} onDone={finishTour} />
        ) : state === "review" ? (
          <MeasurementReview
            key={setup.pairing.pairingId}
            setup={setup}
            onConfirm={(values) => review.mutate(values)}
            pending={review.isPending}
            error={review.error}
          />
        ) : (
          <BuildingState setup={setup} />
        )}
      </main>
      <footer className="setup-bottom">
        {onboardingPreviewEnabled ? (
          <>
            <span>Local preview · workers can stay off</span>
            {(error || !setup || manual || (!isCapture && !repairFace)) && (
              <Link className="setup-text-button" to={previewSetupUrl(destination)}>
                Skip capture & preview next steps <ArrowRight size={14} />
              </Link>
            )}
          </>
        ) : (
          <span>Your fit. Your space.</span>
        )}
      </footer>
    </div>
  );
}

/** Setup is a guided mode, not a trap: Profile and sign-out stay one tap away. */
function SetupAccountMenu({ name, isGuest }: { name: string; isGuest: boolean }) {
  const navigate = useNavigate();
  const { logout } = useAuthMutations();
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (ref.current?.open && !ref.current.contains(e.target as Node)) ref.current.open = false;
    };
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, []);
  return (
    <details className="setup-account" ref={ref}>
      <summary aria-label="Account menu">
        <span aria-hidden>{(name?.[0] ?? "M").toUpperCase()}</span>
      </summary>
      <div className="setup-account__menu">
        <p>
          {name}
          <small>{isGuest ? "Guest account" : "Signed in"}</small>
        </p>
        <Link to="/profile">
          <UserRound size={15} strokeWidth={1.5} /> Profile
        </Link>
        <button
          type="button"
          disabled={logout.isPending}
          onClick={() => logout.mutate(undefined, { onSuccess: () => navigate("/auth/login") })}
        >
          <LogOut size={15} strokeWidth={1.5} /> Sign out
        </button>
      </div>
    </details>
  );
}

const TOUR = [
  {
    clip: "s07-hero-avatar-view",
    title: "Meet your digital twin.",
    text: "An avatar built around your measurements, ready to try things on.",
  },
  {
    clip: "s19-feature-realistic-drape",
    title: "See how it falls.",
    text: "Explore pieces on your avatar and look closely at their shape and drape.",
  },
  {
    clip: "s09-hero-size-choice",
    title: "Find your kind of fit.",
    text: "Compare the available sizes, then save the looks you want to come back to.",
  },
];
export function SetupTour({
  ready,
  onDone,
  preview = false,
}: {
  ready: boolean;
  onDone: () => void;
  preview?: boolean;
}) {
  const [index, setIndex] = useState(0);
  const [failed, setFailed] = useState(false);
  const reduced = useReducedMotion();
  const done = useRef(onDone);
  useEffect(() => {
    done.current = onDone;
  }, [onDone]);
  const videoUrl = import.meta.env.VITE_ONBOARDING_VIDEO_URL;
  useEffect(() => {
    if (reduced || (videoUrl && !failed)) return;
    const id = setTimeout(
      () => (index < TOUR.length - 1 ? setIndex(index + 1) : done.current()),
      4500,
    );
    return () => clearTimeout(id);
  }, [index, reduced, videoUrl, failed]);
  const item = TOUR[index];
  return (
    <section className="setup-tour setup-enter">
      <header className="setup-heading">
        <h1>A quick look around.</h1>
        <p>
          {preview
            ? "A preview of the introduction while your avatar takes shape."
            : "A few ways to make Mirra yours, while your avatar takes shape."}
        </p>
      </header>
      <div className="setup-video-wrap">
        {videoUrl && !failed ? (
          <video
            autoPlay={!reduced}
            muted
            playsInline
            controls
            preload="auto"
            poster={`/mirra/posters/${item.clip}.webp`}
            onEnded={onDone}
            onError={() => setFailed(true)}
          >
            <source src={videoUrl} type="video/mp4" />
          </video>
        ) : (
          <div className="setup-video-placeholder">
            <img src="/profile/capture-front.webp" alt="An example Mirra avatar" />
            <div>
              <span className="setup-placeholder-play">
                <Play size={26} strokeWidth={1.3} />
              </span>
              <h2>Meet Mirra.</h2>
              <p>
                {failed
                  ? "The introduction couldn’t load."
                  : "Your introduction video will play here."}
              </p>
              <span className="setup-preview-badge">Video placeholder</span>
            </div>
          </div>
        )}
        {!videoUrl && (
          <div key={index} className="setup-video-caption setup-enter" aria-live="polite">
            <h2>{item.title}</h2>
            <p>{item.text}</p>
            <span>
              {index + 1} of {TOUR.length}
            </span>
          </div>
        )}
      </div>
      <div className="setup-tour-footer">
        <p role="status">
          {ready ? <Check size={15} /> : <LoaderCircle size={15} className="setup-spinner" />}
          {preview
            ? "Preview continues to the loading screen."
            : ready
              ? "Your avatar is ready to review."
              : "Your avatar is being made in the background."}
        </p>
        <button className="setup-text-button" onClick={onDone}>
          {ready
            ? "Review my measurements"
            : preview
              ? "Continue preview"
              : failed
                ? "Continue without video"
                : "Skip introduction"}
          <ArrowRight size={15} />
        </button>
      </div>
    </section>
  );
}

const NUDGES = [
  "A little patience. A much more personal fit.",
  "Good things are taking shape.",
  "Your next look starts with you.",
];
export function BuildingState({
  setup,
  preview = false,
}: {
  setup: AvatarSetup;
  preview?: boolean;
}) {
  const [nudge, setNudge] = useState(0);
  const reduced = useReducedMotion();
  useEffect(() => {
    if (reduced) return;
    const id = setInterval(() => setNudge((n) => (n + 1) % NUDGES.length), 6500);
    return () => clearInterval(id);
  }, [reduced]);
  const steps = [
    { label: "Photos received", done: setup.pairing.captureComplete },
    {
      label: "Measurements estimated",
      done: setup.capture?.state === "applied" || setup.pairing.measurementMethod === "manual",
    },
    {
      label: setup.pairing.faceSkipped ? "Face photo skipped" : "Your face reconstructed",
      done: setup.pairing.faceSkipped || setup.face?.state === "ready",
    },
    { label: "Avatar created", done: setup.job?.state === "ready" },
  ];
  return (
    <section className="setup-building setup-enter">
      <div className="setup-building-preview" aria-hidden="true">
        <img src="/profile/capture-front.webp" alt="" />
        <span className="setup-building-overlay">
          Bringing you into focus
          <span className="setup-loading-dots" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
        </span>
      </div>
      <div className="setup-building-copy">
        <h1>{setup.state === "updating" ? "Perfecting your fit." : "You, taking shape."}</h1>
        <p role="status">
          {preview
            ? "This is how your avatar’s progress will appear. Next, review a set of example measurements."
            : setup.state === "updating"
              ? "Updating your avatar with your corrections before we open Studio."
              : setup.job?.state === "ready" &&
                  !setup.pairing.faceSkipped &&
                  setup.face?.state !== "ready"
                ? "Adding the finishing touches to your face."
                : (setup.job?.stageLabel ?? "Estimating your measurements from your photos.")}
        </p>
        {!preview && (
          <ol className="setup-build-steps">
            {steps.map((s) => (
              <li key={s.label} data-done={s.done}>
                {s.done ? <Check size={15} /> : <span className="setup-step-dot" />}
                {s.label}
              </li>
            ))}
          </ol>
        )}
        <p key={nudge} className="setup-nudge">
          {NUDGES[nudge]}
        </p>
        <p className="setup-small">
          {preview
            ? "Preview only. No model is running and no data is being saved."
            : "You can leave this tab and come back. Your progress is saved."}
        </p>
      </div>
    </section>
  );
}

export function MeasurementReview({
  setup,
  onConfirm,
  pending,
  error,
  preview,
}: {
  setup: AvatarSetup;
  onConfirm: (v: Partial<Record<PhotoMeasurementField, number>>) => void;
  pending: boolean;
  error: Error | null;
  preview?: React.ReactNode;
}) {
  const review = useMeasurementReview(setup.measurements);
  function confirm(e: React.FormEvent) {
    e.preventDefault();
    if (pending) return;
    const corrections = review.corrections();
    if (corrections) onConfirm(corrections);
  }
  return (
    <section className="setup-review setup-enter">
      <div className="setup-review-preview">
        <span className="setup-ready-tag">
          <Check size={14} />
          {preview ? "Example avatar" : "Your avatar is ready"}
        </span>
        {preview ?? <AvatarGlbViewer className="setup-avatar-view" />}
        <p>{preview ? "Illustration only" : "Drag to turn · scroll to zoom"}</p>
      </div>
      <form onSubmit={confirm} className="setup-review-form">
        <h1>Does this feel like you?</h1>
        <p>
          {preview
            ? "Try reviewing these example measurements. They won’t be saved to your account."
            : "These are your starting measurements. Use a slider or enter a value you’ve checked with a tape measure."}
        </p>
        <div className="setup-review-units" role="group" aria-label="Measurement units">
          <button
            type="button"
            aria-pressed={review.units === "metric"}
            onClick={() => review.setUnits("metric")}
            disabled={pending}
          >
            cm / kg
          </button>
          <button
            type="button"
            aria-pressed={review.units === "imperial"}
            onClick={() => review.setUnits("imperial")}
            disabled={pending}
          >
            in / lb
          </button>
        </div>
        <MeasurementSliders review={review} disabled={pending} />
        {!!setup.capture?.warnings.length && (
          <details className="setup-review-notes">
            <summary>
              Photo notes <ChevronDown size={14} />
            </summary>
            <ul>
              {setup.capture.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          </details>
        )}
        {(review.validation || error) && (
          <p role="alert" className="setup-error">
            {review.validation ?? error?.message}
          </p>
        )}
        <button className="setup-primary" type="submit" disabled={pending}>
          {pending ? <LoaderCircle className="setup-spinner" size={16} /> : null}
          {preview ? "Open Studio" : "Confirm & open Studio"}
          <ArrowRight size={16} />
        </button>
        <p className="setup-small">
          {preview
            ? "This walkthrough leaves your real avatar and measurements unchanged."
            : "Changes are applied to your avatar before Studio opens."}
        </p>
      </form>
    </section>
  );
}
