import { motion, useReducedMotion } from "motion/react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Clock3,
  Mail,
  MailCheck,
  Sparkles,
  Store,
} from "lucide-react";
import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type FormEvent,
  type InputHTMLAttributes,
} from "react";
import { Link } from "react-router-dom";
import { MirraApiError, userMessage } from "@/integrations/mirra-api/errors";
import {
  submitJoinApplication,
  type JoinApplicationResponse,
  type JoinRole,
  type MonthlyOrders,
} from "@/features/join/join-api";
import styles from "./join.module.css";

type JoinForm = {
  name: string;
  email: string;
  company: string;
  website: string;
  role: "" | JoinRole;
  monthlyOrders: "" | MonthlyOrders;
  goals: string;
  consent: boolean;
};

type JoinField = keyof JoinForm;
type JoinErrors = Partial<Record<JoinField, string>>;

const EMPTY_FORM: JoinForm = {
  name: "",
  email: "",
  company: "",
  website: "",
  role: "",
  monthlyOrders: "",
  goals: "",
  consent: false,
};

const ROLE_OPTIONS: ReadonlyArray<{ value: JoinRole; label: string }> = [
  { value: "founder", label: "Founder / leadership" },
  { value: "ecommerce", label: "E-commerce / growth" },
  { value: "product", label: "Product / design" },
  { value: "engineering", label: "Engineering / technology" },
  { value: "other", label: "Something else" },
];

const ORDER_OPTIONS: ReadonlyArray<{ value: "" | MonthlyOrders; label: string }> = [
  { value: "", label: "Prefer not to say" },
  { value: "under-1k", label: "Under 1,000" },
  { value: "1k-10k", label: "1,000–10,000" },
  { value: "10k-50k", label: "10,000–50,000" },
  { value: "50k-plus", label: "50,000+" },
];

function normalizeWebsite(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "";
  return /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`;
}

function validate(form: JoinForm): JoinErrors {
  const errors: JoinErrors = {};
  const email = form.email.trim();
  const website = normalizeWebsite(form.website);

  if (form.name.trim().length < 2) errors.name = "Enter your name.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    errors.email = "Enter a valid work email.";
  }
  if (form.company.trim().length < 2) errors.company = "Enter your company or brand name.";
  if (!form.role) errors.role = "Choose the role closest to yours.";
  if (form.goals.trim().length < 20) {
    errors.goals = "Share a little more so we can prepare for the conversation.";
  }
  if (!form.consent) errors.consent = "Confirm that Mirra may contact you about early access.";

  if (website) {
    try {
      const parsed = new URL(website);
      if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
        errors.website = "Enter a valid website.";
      }
    } catch {
      errors.website = "Enter a valid website, such as yourstore.com.";
    }
  }

  return errors;
}

function TextField({
  error,
  label,
  name,
  optional,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & {
  error?: string;
  label: string;
  name: JoinField;
  optional?: boolean;
}) {
  const errorId = `${name}-error`;

  return (
    <label className={styles.field}>
      <span>
        {label}
        {optional && <small>Optional</small>}
      </span>
      <input
        {...props}
        name={name}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? errorId : undefined}
      />
      {error && (
        <small className={styles.fieldError} id={errorId}>
          {error}
        </small>
      )}
    </label>
  );
}

function SuccessPanel({ email, response }: { email: string; response: JoinApplicationResponse }) {
  const panelRef = useRef<HTMLElement>(null);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    panelRef.current?.focus({ preventScroll: true });
  }, []);

  return (
    <motion.section
      ref={panelRef}
      className={styles.success}
      initial={reducedMotion ? false : { opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={reducedMotion ? { duration: 0 } : { duration: 0.52, ease: [0.22, 1, 0.36, 1] }}
      aria-labelledby="join-success-title"
      aria-live="polite"
      tabIndex={-1}
    >
      <div className={styles.successMark} aria-hidden="true">
        <Check size={25} strokeWidth={1.8} />
      </div>
      <p className={styles.cardLabel}>Application received</p>
      <h2 id="join-success-title">You’re on our radar.</h2>
      <p className={styles.successLead}>
        {response.confirmationEmailSent
          ? `A confirmation is on its way to ${email}. We’ll use the same address when it’s time to talk.`
          : `Your request is safely with our team. We’ll review it and follow up at ${email}.`}
      </p>
      {!response.confirmationEmailSent && (
        <p className={styles.deliveryNote}>
          No automatic confirmation was sent, but your application has been saved.
        </p>
      )}

      <div className={styles.successTimeline} aria-label="What happens next">
        <div>
          <span>01</span>
          <p>
            <strong>We review your store</strong>
            <small>We look at your catalogue, customer journey, and fit use case.</small>
          </p>
        </div>
        <div>
          <span>02</span>
          <p>
            <strong>We reach out by email</strong>
            <small>A Mirra team member will coordinate the next conversation.</small>
          </p>
        </div>
        <div>
          <span>03</span>
          <p>
            <strong>We shape the right test</strong>
            <small>Together, we’ll decide whether a focused pilot makes sense.</small>
          </p>
        </div>
      </div>

      <div className={styles.successActions}>
        <Link to="/" className={styles.primaryLink}>
          Explore Mirra
          <ArrowRight size={17} strokeWidth={1.7} />
        </Link>
        <span>Reference {response.applicationId}</span>
      </div>
    </motion.section>
  );
}

export default function Join() {
  const reducedMotion = useReducedMotion();
  const [form, setForm] = useState<JoinForm>(EMPTY_FORM);
  const [errors, setErrors] = useState<JoinErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<JoinApplicationResponse | null>(null);
  const successEmail = useRef("");

  const updateField = (
    event: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    const name = event.target.name as JoinField;
    const value = event.target.value;
    setForm((current) => ({ ...current, [name]: value }));
    setErrors((current) => (current[name] ? { ...current, [name]: undefined } : current));
    setSubmitError(null);
  };

  const updateConsent = (event: ChangeEvent<HTMLInputElement>) => {
    setForm((current) => ({ ...current, consent: event.target.checked }));
    setErrors((current) => (current.consent ? { ...current, consent: undefined } : current));
    setSubmitError(null);
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextErrors = validate(form);
    setErrors(nextErrors);
    setSubmitError(null);

    if (Object.keys(nextErrors).length > 0) {
      const firstError = Object.keys(nextErrors)[0] as JoinField | undefined;
      const firstInvalid = firstError
        ? event.currentTarget.querySelector<HTMLElement>(`[name="${firstError}"]`)
        : null;
      firstInvalid?.focus();
      return;
    }

    const email = form.email.trim().toLowerCase();
    setSubmitting(true);

    try {
      const response = await submitJoinApplication({
        name: form.name.trim(),
        email,
        company: form.company.trim(),
        ...(form.website.trim() ? { website: normalizeWebsite(form.website) } : {}),
        role: form.role as JoinRole,
        ...(form.monthlyOrders ? { monthlyOrders: form.monthlyOrders } : {}),
        goals: form.goals.trim(),
      });
      successEmail.current = email;
      setResult(response);
    } catch (error) {
      if (error instanceof MirraApiError) {
        setSubmitError(userMessage(error.code));
      } else {
        setSubmitError("We couldn’t save your request. Your answers are still here—please retry.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const motionProps = reducedMotion
    ? {}
    : {
        initial: { opacity: 0, y: 24 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.7, ease: [0.22, 1, 0.36, 1] as const },
      };

  return (
    <main className={styles.page} id="top" data-header="light" data-nav-label="JOIN MIRRA">
      <div className={styles.grid} aria-hidden="true" />
      <section className={styles.hero} aria-labelledby="join-title">
        <motion.div
          className={styles.formColumn}
          {...(reducedMotion
            ? {}
            : {
                initial: { opacity: 0, y: 30 },
                animate: { opacity: 1, y: 0 },
                transition: { duration: 0.76, delay: 0.08, ease: [0.22, 1, 0.36, 1] },
              })}
        >
          {result ? (
            <SuccessPanel email={successEmail.current} response={result} />
          ) : (
            <form className={styles.formCard} onSubmit={onSubmit} aria-busy={submitting} noValidate>
              <div className={styles.formHeading}>
                <p className={styles.formPill}>Join Mirra</p>
                <h2>Apply to test the fit experience.</h2>
                <span className={styles.formTime}>
                  <Clock3 size={15} strokeWidth={1.7} aria-hidden="true" />
                  About 2 min
                </span>
              </div>

              <div className={styles.formBody}>
                <div className={styles.twoColumns}>
                  <TextField
                    label="Your name"
                    name="name"
                    value={form.name}
                    onChange={updateField}
                    error={errors.name}
                    autoComplete="name"
                    placeholder="Avery Chen"
                    maxLength={100}
                    required
                  />
                  <TextField
                    label="Work email"
                    name="email"
                    type="email"
                    value={form.email}
                    onChange={updateField}
                    error={errors.email}
                    autoComplete="email"
                    placeholder="avery@yourbrand.com"
                    maxLength={254}
                    required
                  />
                </div>

                <TextField
                  label="Company or brand"
                  name="company"
                  value={form.company}
                  onChange={updateField}
                  error={errors.company}
                  autoComplete="organization"
                  placeholder="Your brand"
                  maxLength={120}
                  required
                />

                <TextField
                  label="Store website"
                  name="website"
                  type="url"
                  value={form.website}
                  onChange={updateField}
                  error={errors.website}
                  autoComplete="url"
                  placeholder="yourbrand.com"
                  maxLength={300}
                  optional
                />

                <label className={styles.field}>
                  <span>Your role</span>
                  <select
                    name="role"
                    value={form.role}
                    onChange={updateField}
                    aria-invalid={Boolean(errors.role)}
                    aria-describedby={errors.role ? "role-error" : undefined}
                    required
                  >
                    <option value="" disabled>
                      Choose one
                    </option>
                    {ROLE_OPTIONS.map((option) => (
                      <option value={option.value} key={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  {errors.role && (
                    <small className={styles.fieldError} id="role-error">
                      {errors.role}
                    </small>
                  )}
                </label>

                <fieldset className={styles.orderField}>
                  <legend>
                    <span>Monthly orders</span>
                    <small>Optional</small>
                  </legend>
                  <div className={styles.orderPills}>
                    {ORDER_OPTIONS.map((option) => (
                      <label className={styles.orderPill} key={option.value || "not-sure"}>
                        <input
                          type="radio"
                          name="monthlyOrders"
                          value={option.value}
                          checked={form.monthlyOrders === option.value}
                          onChange={updateField}
                        />
                        <span>{option.label}</span>
                      </label>
                    ))}
                  </div>
                </fieldset>

                <label className={styles.field}>
                  <span>What would you like to test?</span>
                  <textarea
                    name="goals"
                    value={form.goals}
                    onChange={updateField}
                    aria-invalid={Boolean(errors.goals)}
                    aria-describedby={errors.goals ? "goals-hint goals-error" : "goals-hint"}
                    placeholder="Tell us about your catalogue, shoppers, or the fit problem you want Mirra to help solve."
                    rows={4}
                    maxLength={1200}
                    required
                  />
                  <span className={styles.textareaMeta} id="goals-hint">
                    <small>Keep it brief—specifics help.</small>
                    <small>{form.goals.length}/1200</small>
                  </span>
                  {errors.goals && (
                    <small className={styles.fieldError} id="goals-error">
                      {errors.goals}
                    </small>
                  )}
                </label>

                <div className={styles.consentBlock}>
                  <label className={styles.consentControl}>
                    <input
                      type="checkbox"
                      name="consent"
                      checked={form.consent}
                      onChange={updateConsent}
                      aria-invalid={Boolean(errors.consent)}
                      aria-describedby={
                        errors.consent ? "consent-note consent-error" : "consent-note"
                      }
                      required
                    />
                    <span>
                      Mirra may contact me by email about early access and a possible pilot.
                    </span>
                  </label>
                  <p id="consent-note">
                    By continuing, you acknowledge our <Link to="/terms">Terms</Link> and{" "}
                    <Link to="/privacy">Privacy overview</Link>.
                  </p>
                  {errors.consent && (
                    <small className={styles.fieldError} id="consent-error">
                      {errors.consent}
                    </small>
                  )}
                </div>
              </div>

              {submitError && (
                <div className={styles.submitError} role="alert">
                  <span aria-hidden="true">!</span>
                  <p>
                    <strong>We couldn’t send that yet.</strong>
                    {submitError}
                  </p>
                </div>
              )}

              <button type="submit" className={styles.submitButton} disabled={submitting}>
                <span>{submitting ? "Sending…" : "Join"}</span>
                <span className={styles.submitIcon} aria-hidden="true">
                  {submitting ? <i /> : <ArrowRight size={18} strokeWidth={1.7} />}
                </span>
              </button>
              <span className={styles.srOnly} role="status" aria-live="polite">
                {submitting ? "Submitting your application." : ""}
              </span>

              <p className={styles.emailPromise}>
                <Mail size={15} strokeWidth={1.6} aria-hidden="true" />
                Follow-up happens by email, never through a surprise sales call.
              </p>
            </form>
          )}
        </motion.div>

        <motion.div className={styles.intro} {...motionProps}>
          <div className={styles.introTopline}>
            <Link to="/" className={styles.backLink}>
              <ArrowLeft size={15} strokeWidth={1.7} />
              Back to Mirra
            </Link>
            <p className={styles.eyebrow}>
              <span aria-hidden="true" />
              Early access
            </p>
          </div>

          <div className={styles.introHeader}>
            <h1 id="join-title">
              Make fit feel <span>obvious.</span>
            </h1>
            <p className={styles.lead}>
              Tell us where fit gets in the way for your store. We’ll review your application and
              follow up by email with the most useful next step.
            </p>
          </div>

          <div className={styles.process} aria-label="How joining Mirra works">
            <article>
              <span className={styles.stepIcon} aria-hidden="true">
                <Store size={17} strokeWidth={1.6} />
              </span>
              <div>
                <span className={styles.stepNumber}>01</span>
                <h2>Tell us about your store</h2>
                <p>A focused two-minute application.</p>
              </div>
            </article>
            <article>
              <span className={styles.stepIcon} aria-hidden="true">
                <MailCheck size={17} strokeWidth={1.6} />
              </span>
              <div>
                <span className={styles.stepNumber}>02</span>
                <h2>Hear from a real person</h2>
                <p>Our team reviews every request and responds by email.</p>
              </div>
            </article>
            <article>
              <span className={styles.stepIcon} aria-hidden="true">
                <Sparkles size={17} strokeWidth={1.6} />
              </span>
              <div>
                <span className={styles.stepNumber}>03</span>
                <h2>Test Mirra with intent</h2>
                <p>If there’s a fit, we’ll shape a useful pilot around your store.</p>
              </div>
            </article>
          </div>

          <div className={styles.proof}>
            <p>One focused use case. A real store. A useful answer before any rollout.</p>
            <span>Our pilot principle</span>
          </div>

          <p className={styles.platformNote}>
            <span aria-hidden="true" />
            Built for Shopify · No replatforming
          </p>
        </motion.div>
      </section>
    </main>
  );
}
