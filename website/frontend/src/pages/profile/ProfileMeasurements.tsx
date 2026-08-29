import { useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MeasurementForm } from "@/features/profile/components/measurement-form";
import { useAvatarProfile, useAccount } from "@/hooks/use-shopper";
import {
  CalendarDays,
  ChevronDown,
  Layers3,
  ShieldCheck,
  Shirt,
  SlidersHorizontal,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import type { MeasurementField, MeasurementKey } from "@/integrations/mirra-api/types";
import { track } from "@/lib/analytics";
import { clampMeasurement, cmToInches, inchesToCm, lbToKg, type UnitSystem } from "@/lib/units";

type FitChoice = "close" | "regular" | "relaxed";
type FitGroup = "tops" | "bottoms" | "outerwear";

const FIT_OPTIONS: FitChoice[] = ["close", "regular", "relaxed"];
const DISPLAY_MEASUREMENTS: MeasurementKey[] = [
  "height",
  "chest",
  "waist",
  "hips",
  "inseam",
  "shoulderWidth",
];

const LABEL_OVERRIDES: Partial<Record<MeasurementKey, string>> = {
  hips: "Hip",
  shoulderWidth: "Shoulder",
};

const DEFAULT_FIT: Record<FitGroup, FitChoice> = {
  tops: "regular",
  bottoms: "regular",
  outerwear: "relaxed",
};

function parseFitPreferences(value: string | null): Record<FitGroup, FitChoice> {
  if (!value) return DEFAULT_FIT;
  const parsed: unknown = JSON.parse(value);
  if (!parsed || typeof parsed !== "object") return DEFAULT_FIT;
  const candidate = parsed as Partial<Record<FitGroup, unknown>>;
  return {
    tops: FIT_OPTIONS.includes(candidate.tops as FitChoice)
      ? (candidate.tops as FitChoice)
      : DEFAULT_FIT.tops,
    bottoms: FIT_OPTIONS.includes(candidate.bottoms as FitChoice)
      ? (candidate.bottoms as FitChoice)
      : DEFAULT_FIT.bottoms,
    outerwear: FIT_OPTIONS.includes(candidate.outerwear as FitChoice)
      ? (candidate.outerwear as FitChoice)
      : DEFAULT_FIT.outerwear,
  };
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

function displayMeasurement(field: MeasurementField, value: number, units: UnitSystem) {
  if (units === "metric") {
    return { value: Number(value.toFixed(1)), unit: field.unit };
  }
  if (field.unit === "kg") {
    return { value: Math.round(value * 2.20462), unit: "lb" };
  }
  return { value: cmToInches(value), unit: "in" };
}

function metricMeasurement(field: MeasurementField, value: number, units: UnitSystem) {
  const metric =
    units === "metric" ? value : field.unit === "kg" ? lbToKg(value) : inchesToCm(value);
  return clampMeasurement(metric, field.min, field.max);
}

export default function ProfileMeasurements() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { data: account } = useAccount();
  const { data: avatar, isLoading } = useAvatarProfile(!!account);
  const [draft, setDraft] = useState<Partial<Record<MeasurementKey, number>>>({});
  const [units, setUnits] = useState<UnitSystem>("metric");
  const initializedAvatar = useRef<string | null>(null);
  const [editingKey, setEditingKey] = useState<MeasurementKey | null>(null);
  const [editingValue, setEditingValue] = useState("");
  const [fit, setFit] = useState<Record<FitGroup, FitChoice>>(DEFAULT_FIT);
  const [savedFit, setSavedFit] = useState<Record<FitGroup, FitChoice>>(DEFAULT_FIT);
  const fitStorageKey = account ? `mirra.fit-preferences.${account.shopperId}` : null;
  const unitStorageKey = account ? `mirra.display-units.${account.shopperId}` : null;

  useEffect(() => {
    if (!fitStorageKey) return;
    try {
      const storedFit = parseFitPreferences(sessionStorage.getItem(fitStorageKey));
      setFit(storedFit);
      setSavedFit(storedFit);
    } catch {
      setFit(DEFAULT_FIT);
      setSavedFit(DEFAULT_FIT);
    }
  }, [fitStorageKey]);

  useEffect(() => {
    if (avatar && initializedAvatar.current !== avatar.avatarProfileId) {
      let preferredUnits: UnitSystem = avatar.unitsPreference;
      if (unitStorageKey) {
        try {
          const stored = sessionStorage.getItem(unitStorageKey);
          if (stored === "metric" || stored === "imperial") preferredUnits = stored;
        } catch {
          // Fall back to the profile preference when browser storage is unavailable.
        }
      }
      setUnits(preferredUnits);
      initializedAvatar.current = avatar.avatarProfileId;
    }
  }, [avatar, unitStorageKey]);

  const save = useMutation({
    mutationFn: async () => {
      let profile = avatar;
      if (avatar && Object.keys(draft).length > 0) {
        profile = await getRuntimeProvider().updateMeasurements(draft);
      }
      if (fitStorageKey) {
        try {
          sessionStorage.setItem(fitStorageKey, JSON.stringify(fit));
        } catch {
          // Fit controls are an optional, device-local enhancement.
        }
      }
      return profile;
    },
    onSuccess: (profile) => {
      if (profile) qc.setQueryData(["account", "avatar-profile"], profile);
      if (Object.keys(draft).length > 0) {
        track("measurements_updated", { authenticated: true });
      }
      setDraft({});
      setSavedFit(fit);
      setEditingKey(null);
      setEditingValue("");
    },
  });

  if (isLoading) return <ProfileMeasurementsLoading />;

  if (!avatar) {
    return (
      <div className="profile-measurements-page profile-measurements-empty">
        <section className="profile-panel profile-measurements-empty__card">
          <p className="profile-meta">Measurements &amp; preferences</p>
          <h1>Fit profile</h1>
          <p>
            Add your measurements below. Once they&apos;re saved you can generate your avatar from
            the Avatar tab.
          </p>
          {/* The old standalone /measurements page is gone — this page is now
              the only measurement entry point (doc 13, D7). */}
          <MeasurementForm onSaved={() => navigate("/profile/avatar")} />
        </section>
      </div>
    );
  }

  const measurements = DISPLAY_MEASUREMENTS.map((key) =>
    avatar.measurements.find((field) => field.key === key && field.supported),
  ).filter((field): field is MeasurementField => Boolean(field));
  const weight = avatar.measurements.find((field) => field.key === "weight" && field.supported);
  const supportedMeasurements = avatar.measurements.filter((field) => field.supported);
  const confirmedMeasurements = supportedMeasurements.filter(
    (field) => !field.estimated || Object.prototype.hasOwnProperty.call(draft, field.key),
  );
  const completeness = supportedMeasurements.length
    ? Math.round((confirmedMeasurements.length / supportedMeasurements.length) * 100)
    : 0;
  const hasChanges =
    Object.keys(draft).length > 0 ||
    (Object.keys(DEFAULT_FIT) as FitGroup[]).some((key) => fit[key] !== savedFit[key]);

  function beginEditing(field: MeasurementField) {
    const value = displayMeasurement(field, draft[field.key] ?? field.value, units).value;
    setEditingValue(String(value));
    setEditingKey(field.key);
  }

  function cancelEditing() {
    setEditingKey(null);
    setEditingValue("");
  }

  function commitEditing(field: MeasurementField) {
    const next = Number(editingValue);
    if (editingValue.trim() !== "" && Number.isFinite(next)) {
      save.reset();
      setDraft((current) => ({
        ...current,
        [field.key]: metricMeasurement(field, next, units),
      }));
    }
    cancelEditing();
  }

  return (
    <div className="profile-measurements-page">
      <div className="profile-measurements-main">
        <header className="profile-page-heading profile-measurements-heading">
          <p className="profile-meta">Measurements &amp; preferences</p>
          <h1>Fit profile</h1>
          <p>
            Tell us your measurements and fit preferences.
            <br />
            We&apos;ll use this to recommend the right size and fit.
          </p>
        </header>

        <section className="profile-measurements-section" aria-labelledby="measurements-title">
          <div className="profile-measurements-section__header">
            <h2 id="measurements-title">Your measurements</h2>
            <p>Edit any value directly in the list.</p>
          </div>

          <div className="profile-measurement-table">
            {measurements.map((field) => {
              const metricValue = draft[field.key] ?? field.value;
              const display = displayMeasurement(field, metricValue, units);
              const editing = editingKey === field.key;
              return (
                <div className="profile-measurement-table__row" key={field.key}>
                  <label htmlFor={`profile-measurement-${field.key}`}>
                    <span>{LABEL_OVERRIDES[field.key] ?? field.label}</span>
                    {field.estimated && !Object.prototype.hasOwnProperty.call(draft, field.key) && (
                      <em>Estimated</em>
                    )}
                  </label>
                  <div className="profile-measurement-table__value">
                    {editing ? (
                      <>
                        <input
                          id={`profile-measurement-${field.key}`}
                          type="number"
                          inputMode="decimal"
                          min={displayMeasurement(field, field.min, units).value}
                          max={displayMeasurement(field, field.max, units).value}
                          step={units === "imperial" ? 0.5 : field.step}
                          value={editingValue}
                          onChange={(event) => setEditingValue(event.target.value)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter") commitEditing(field);
                            if (event.key === "Escape") cancelEditing();
                          }}
                          autoFocus
                        />
                        <span>{display.unit}</span>
                      </>
                    ) : (
                      `${display.value} ${display.unit}`
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => (editing ? commitEditing(field) : beginEditing(field))}
                    aria-label={`${editing ? "Finish editing" : "Edit"} ${field.label}`}
                  >
                    {editing ? "Done" : "Edit"}
                  </button>
                </div>
              );
            })}
          </div>
        </section>

        <section className="profile-fit-section" aria-labelledby="fit-title">
          <h2 id="fit-title">How you like clothes to fit</h2>
          <div className="profile-fit-table">
            <FitRow
              icon={<Shirt aria-hidden size={19} strokeWidth={1.45} />}
              label="Tops"
              value={fit.tops}
              onChange={(value) => {
                save.reset();
                setFit((current) => ({ ...current, tops: value }));
              }}
            />
            <FitRow
              icon={<SlidersHorizontal aria-hidden size={19} strokeWidth={1.45} />}
              label="Bottoms"
              value={fit.bottoms}
              onChange={(value) => {
                save.reset();
                setFit((current) => ({ ...current, bottoms: value }));
              }}
            />
            <FitRow
              icon={<Layers3 aria-hidden size={19} strokeWidth={1.45} />}
              label="Outerwear"
              value={fit.outerwear}
              onChange={(value) => {
                save.reset();
                setFit((current) => ({ ...current, outerwear: value }));
              }}
            />
          </div>
        </section>

        <details className="profile-more-fit">
          <summary>
            <span className="profile-fit-icon">
              <SlidersHorizontal aria-hidden size={19} strokeWidth={1.45} />
            </span>
            <span>
              <strong>More fit preferences</strong>
              <small>Trouser rise, break, top length, sleeve feel and more.</small>
            </span>
            <ChevronDown aria-hidden size={20} strokeWidth={1.6} />
          </summary>
          <div className="profile-more-fit__content">
            <div>
              <span className="profile-more-fit__label">
                <span>Display units</span>
                <small>Saved for this browser session</small>
              </span>
              <div className="profile-unit-switch" role="group" aria-label="Measurement units">
                {(["metric", "imperial"] as const).map((option) => (
                  <button
                    key={option}
                    type="button"
                    aria-pressed={units === option}
                    className={units === option ? "profile-unit-switch--active" : ""}
                    onClick={() => {
                      setUnits(option);
                      if (unitStorageKey) {
                        try {
                          sessionStorage.setItem(unitStorageKey, option);
                        } catch {
                          // The conversion still works for the current view.
                        }
                      }
                    }}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>
            {weight && (
              <div>
                <span>Weight</span>
                <span className="profile-more-fit__measure">
                  {editingKey === "weight" ? (
                    <>
                      <input
                        id="profile-measurement-weight"
                        type="number"
                        inputMode="decimal"
                        min={displayMeasurement(weight, weight.min, units).value}
                        max={displayMeasurement(weight, weight.max, units).value}
                        step={units === "imperial" ? 1 : weight.step}
                        value={editingValue}
                        onChange={(event) => setEditingValue(event.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") commitEditing(weight);
                          if (event.key === "Escape") cancelEditing();
                        }}
                        autoFocus
                      />
                      <span>
                        {displayMeasurement(weight, draft.weight ?? weight.value, units).unit}
                      </span>
                    </>
                  ) : (
                    <span>
                      {displayMeasurement(weight, draft.weight ?? weight.value, units).value}{" "}
                      {displayMeasurement(weight, draft.weight ?? weight.value, units).unit}
                    </span>
                  )}
                  <button
                    type="button"
                    aria-label={`${editingKey === "weight" ? "Finish editing" : "Edit"} Weight`}
                    onClick={() =>
                      editingKey === "weight" ? commitEditing(weight) : beginEditing(weight)
                    }
                  >
                    {editingKey === "weight" ? "Done" : "Edit"}
                  </button>
                </span>
              </div>
            )}
          </div>
        </details>
      </div>

      <aside className="profile-panel profile-fit-summary">
        <div>
          <h2>Profile completeness</h2>
          <p className="profile-fit-summary__score">{completeness}%</p>
          <div
            className="profile-fit-summary__progress"
            role="progressbar"
            aria-label="Profile completeness"
            aria-valuenow={completeness}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <span style={{ width: `${completeness}%` }} />
          </div>
          <p className="profile-fit-summary__hint">
            {completeness === 100
              ? "Your measurement profile is complete."
              : "Confirm estimated details to improve recommendations."}
          </p>
        </div>

        <div className="profile-fit-summary__detail profile-fit-summary__detail--first">
          <div>
            <h3>Profile updated</h3>
            <p>{formatDate(avatar.updatedAt)}</p>
          </div>
          <span>
            <CalendarDays aria-hidden size={18} strokeWidth={1.55} />
          </span>
        </div>

        <div className="profile-fit-summary__detail">
          <div>
            <h3>Saved to profile</h3>
            <p>
              Measurements sync to your profile. Fit controls stay local to this browser session.
            </p>
          </div>
          <span>
            <ShieldCheck aria-hidden size={18} strokeWidth={1.55} />
          </span>
        </div>

        {save.error && (
          <p className="profile-inline-error" role="alert">
            {save.error instanceof Error ? save.error.message : "Saving did not complete."}
          </p>
        )}

        {save.isSuccess && !save.error && (
          <p className="profile-inline-success" role="status">
            Your fit profile changes are saved.
          </p>
        )}

        <button
          type="button"
          className="profile-dark-button profile-fit-summary__save"
          disabled={save.isPending || !hasChanges}
          onClick={() => save.mutate()}
        >
          {save.isPending ? "Saving…" : save.isSuccess && !hasChanges ? "Saved" : "Save changes"}
        </button>
        <Link to="/studio" className="profile-fit-summary__studio">
          Review in studio <span aria-hidden>→</span>
        </Link>
      </aside>
    </div>
  );
}

function ProfileMeasurementsLoading() {
  return (
    <div className="profile-measurements-page profile-page-loading" aria-busy="true" role="status">
      <div className="profile-measurements-main" aria-hidden>
        <div className="profile-loading-copy">
          <span className="profile-loading-block profile-loading-block--meta" />
          <span className="profile-loading-block profile-loading-block--title" />
          <span className="profile-loading-block profile-loading-block--copy" />
        </div>
        <span className="profile-loading-block profile-loading-block--table" />
        <span className="profile-loading-block profile-loading-block--table" />
      </div>
      <span
        className="profile-loading-block profile-loading-block--panel profile-loading-block--summary"
        aria-hidden
      />
      <span className="sr-only">Loading your fit profile…</span>
    </div>
  );
}

function FitRow({
  icon,
  label,
  value,
  onChange,
}: {
  icon: React.ReactNode;
  label: string;
  value: FitChoice;
  onChange: (value: FitChoice) => void;
}) {
  return (
    <div className="profile-fit-row">
      <span className="profile-fit-icon">{icon}</span>
      <span className="profile-fit-row__label">{label}</span>
      <div className="profile-fit-segments" role="group" aria-label={`${label} fit`}>
        {FIT_OPTIONS.map((option) => (
          <button
            key={option}
            type="button"
            aria-pressed={value === option}
            className={value === option ? "profile-fit-segment--active" : ""}
            onClick={() => onChange(option)}
          >
            {option[0].toUpperCase() + option.slice(1)}
          </button>
        ))}
      </div>
    </div>
  );
}
