import type { ReactNode } from "react";

export function SocialButtonRow({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-center justify-center gap-3">
      {children}
    </div>
  );
}

export function GoogleIconButton({
  onClick,
  loading,
}: {
  onClick: () => void;
  loading?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      aria-label="Continue with Google"
      className="pressable flex size-11 items-center justify-center rounded-xl border border-black/10 bg-white shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-all hover:border-black/25 hover:bg-neutral-50/80 active:scale-95 disabled:opacity-50"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden>
        <path
          d="M21.6 12.23c0-.68-.06-1.36-.19-2.02H12v3.83h5.4a4.6 4.6 0 0 1-2 3.02v2.5h3.22c1.89-1.73 2.98-4.3 2.98-7.33Z"
          fill="#000000"
        />
        <path
          d="M12 22c2.7 0 4.97-.89 6.62-2.42l-3.22-2.5c-.9.6-2.05.95-3.4.95-2.6 0-4.81-1.76-5.6-4.12H3.06v2.58A10 10 0 0 0 12 22Z"
          fill="#000000"
        />
        <path
          d="M6.4 13.9a6 6 0 0 1 0-3.82V7.5H3.06a10 10 0 0 0 0 8.98L6.4 13.9Z"
          fill="#000000"
        />
        <path
          d="M12 5.96c1.47 0 2.79.5 3.82 1.5l2.86-2.86A9.97 9.97 0 0 0 12 2 10 10 0 0 0 3.06 7.5L6.4 10.1C7.19 7.73 9.4 5.96 12 5.96Z"
          fill="#000000"
        />
      </svg>
    </button>
  );
}

export function GithubIconButton({
  onClick,
  loading,
}: {
  onClick?: () => void;
  loading?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      aria-label="Continue with GitHub"
      className="pressable flex size-11 items-center justify-center rounded-xl border border-black/10 bg-white shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-all hover:border-black/25 hover:bg-neutral-50/80 active:scale-95 disabled:opacity-50"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
        <path
          fillRule="evenodd"
          clipRule="evenodd"
          d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
        />
      </svg>
    </button>
  );
}

/** Full-width Google button kept for backward compatibility with older pages. */
export function GoogleButton({ onClick, loading }: { onClick: () => void; loading?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      aria-label="Continue with Google"
      className="auth-oauth-button pressable flex h-12 w-full items-center justify-center gap-3 rounded-xl border border-black/10 bg-white px-5 text-sm font-medium text-ink shadow-[0_1px_2px_rgba(0,0,0,0.04)] hover:border-black/25 hover:bg-neutral-50/80 active:scale-[0.99] disabled:opacity-50"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden>
        <path
          d="M21.6 12.23c0-.68-.06-1.36-.19-2.02H12v3.83h5.4a4.6 4.6 0 0 1-2 3.02v2.5h3.22c1.89-1.73 2.98-4.3 2.98-7.33Z"
          fill="#4285F4"
        />
        <path
          d="M12 22c2.7 0 4.97-.89 6.62-2.42l-3.22-2.5c-.9.6-2.05.95-3.4.95-2.6 0-4.81-1.76-5.6-4.12H3.06v2.58A10 10 0 0 0 12 22Z"
          fill="#34A853"
        />
        <path d="M6.4 13.9a6 6 0 0 1 0-3.82V7.5H3.06a10 10 0 0 0 0 8.98L6.4 13.9Z" fill="#FBBC04" />
        <path
          d="M12 5.96c1.47 0 2.79.5 3.82 1.5l2.86-2.86A9.97 9.97 0 0 0 12 2 10 10 0 0 0 3.06 7.5L6.4 10.1C7.19 7.73 9.4 5.96 12 5.96Z"
          fill="#EA4335"
        />
      </svg>
      <span>{loading ? "Connecting…" : "Continue with Google"}</span>
    </button>
  );
}
