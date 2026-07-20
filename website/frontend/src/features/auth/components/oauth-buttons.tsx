/**
 * Google is required; the layout is Apple-ready (add an AppleButton beside
 * GoogleButton when the provider is configured).
 */
export function GoogleButton({ onClick, loading }: { onClick: () => void; loading?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={loading}
      aria-label="Continue with Google"
      className="pressable flex h-12.5 w-full items-center justify-center gap-3 rounded-[14px] border border-line-strong bg-paper/90 px-5 text-sm font-semibold text-ink shadow-[0_1px_0_rgba(255,255,255,0.9)_inset] hover:border-ink/50 hover:bg-paper disabled:opacity-50"
    >
      <svg width="19" height="19" viewBox="0 0 24 24" aria-hidden>
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
