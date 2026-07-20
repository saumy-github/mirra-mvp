import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Check, X, Mail } from "lucide-react";

/**
 * Extracted from Mirra-landing-page's App.tsx (was inline). Posts to
 * {apiBaseUrl}/waitlist — until the backend's waitlist endpoint exists this
 * will hit the network-error path, which the modal already handles
 * gracefully (see the "couldn't submit" message below).
 */
export function WaitlistModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!email) return;
    setStatus("loading");
    try {
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
      const res = await fetch(`${apiBaseUrl}/waitlist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      const contentType = res.headers.get("content-type");
      let data: { message?: string; error?: string } = {};
      if (contentType && contentType.includes("application/json")) {
        data = await res.json();
      }

      if (res.ok) {
        setStatus("success");
        setMessage(data.message || "You're on the list!");
      } else {
        setStatus("error");
        if (res.status === 400) {
          setMessage(data.error || "Please enter a valid email address.");
        } else if (res.status === 409) {
          setMessage(data.error || "This email is already registered!");
        } else if (res.status === 500) {
          setMessage("Internal server error. Please try again later.");
        } else {
          setMessage(data.error || "Something went wrong. Please try again.");
        }
      }
    } catch {
      setStatus("error");
      setMessage("We couldn't submit your email right now. Please try again in a moment.");
    }
  };

  const handleClose = () => {
    setEmail("");
    setStatus("idle");
    setMessage("");
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-200 flex items-center justify-center p-4"
          onClick={handleClose}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-bg/85 backdrop-blur-md" />

          {/* Close button outside pill */}
          <button
            onClick={handleClose}
            aria-label="Close"
            className="absolute top-8 right-8 z-10 flex h-10 w-10 items-center justify-center rounded-full bg-surface text-muted transition-all hover:bg-wine/10 hover:text-ink"
          >
            <X size={20} />
          </button>

          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="relative z-10 w-full max-w-150"
            onClick={(e) => e.stopPropagation()}
          >
            <AnimatePresence mode="wait">
              {status === "success" ? (
                <motion.div
                  key="success"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="waitlist-pill flex-col justify-center py-8 text-center"
                >
                  <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-full border border-soft-green/30 bg-soft-green/20">
                    <Check size={20} className="text-soft-green" />
                  </div>
                  <h3 className="mb-1 text-xl font-bold text-ink">You're in! 🎉</h3>
                  <p className="mb-4 text-sm text-muted">{message}</p>
                  <button
                    onClick={handleClose}
                    className="rounded-full border border-silver px-6 py-2 text-sm font-medium text-muted transition-all hover:border-wine/50 hover:text-ink"
                  >
                    Close
                  </button>
                </motion.div>
              ) : (
                <motion.div
                  key="form"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="flex w-full flex-col items-center"
                >
                  <div className="mb-8 text-center">
                    <h3 className="mb-2 text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
                      Get early access to Mirra
                    </h3>
                    <p className="text-sm text-muted">
                      Leave your email and we'll reach out to schedule a live walkthrough.
                    </p>
                  </div>
                  <form onSubmit={handleSubmit} className="waitlist-pill">
                    <Mail size={24} className="waitlist-action-icon" />

                    <input
                      type="email"
                      className="waitlist-input"
                      placeholder="your@email.com"
                      spellCheck="false"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />

                    {status === "loading" ? (
                      <div className="flex h-12 w-12 items-center justify-center">
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                          className="h-5 w-5 rounded-full border-2 border-silver border-t-wine"
                        />
                      </div>
                    ) : (
                      <div className="relative flex items-center gap-4">
                        {status === "error" && (
                          <p className="absolute right-0 -bottom-8 left-0 text-center text-xs text-rose">
                            {message}
                          </p>
                        )}
                        <button
                          type="submit"
                          aria-label="Join the waitlist"
                          className="liquid-metal-btn shadow-md"
                        >
                          <svg
                            viewBox="0 0 1024 1024"
                            version="1.1"
                            xmlns="http://www.w3.org/2000/svg"
                            aria-hidden="true"
                            fill="currentColor"
                          >
                            <path d="M843.968 896a51.072 51.072 0 0 1-51.968-52.032V232H180.032A51.072 51.072 0 0 1 128 180.032c0-29.44 22.528-52.032 52.032-52.032h663.936c29.44 0 52.032 22.528 52.032 52.032v663.936c0 29.44-22.528 52.032-52.032 52.032z"></path>
                            <path d="M180.032 896a49.92 49.92 0 0 1-36.48-15.616c-20.736-20.8-20.736-53.76 0-72.832L807.616 143.616c20.864-20.8 53.76-20.8 72.832 0 20.8 20.8 20.8 53.76 0 72.768L216.384 880.384a47.232 47.232 0 0 1-36.352 15.616z"></path>
                          </svg>
                        </button>
                      </div>
                    )}
                  </form>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
