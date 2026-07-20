import { useAccount } from "@/hooks/use-shopper";
import { useSignatureLookMutations, useSignatureLooks } from "@/hooks/use-signature-looks";

export default function ProfileSignatureLooks() {
  const { data: account } = useAccount();
  const { data: looks = [], isLoading } = useSignatureLooks(!!account);
  const { updateLook, deleteLook } = useSignatureLookMutations();

  if (isLoading) return null;

  if (looks.length === 0) {
    return (
      <p className="text-sm leading-relaxed text-muted">
        No Signature Looks yet. In the studio, dress your avatar in a base outfit you like and
        choose <span className="font-mono text-xs">✦ MAKE SIGNATURE LOOK</span> — new garments will
        then be tried over clothes you actually wear.
      </p>
    );
  }

  return (
    <ul className="space-y-4">
      {looks.map((look) => (
        <li
          key={look.lookId}
          className="flex items-center gap-5 rounded-[14px] border border-line bg-surface p-4"
        >
          <div className="flex size-16 items-center justify-center overflow-hidden rounded-full border border-line-strong bg-paper p-2">
            {look.thumbnailUrl ? (
              <img src={look.thumbnailUrl} alt="" className="h-full w-full object-contain" />
            ) : (
              <span className="text-xs text-muted">{look.name.slice(0, 2)}</span>
            )}
          </div>
          <div className="min-w-0 flex-1">
            <p className="font-medium">
              {look.name}
              {look.isDefault && (
                <span className="ml-2 rounded-full bg-mist px-2 py-0.5 text-[10px] tracking-wider text-muted uppercase">
                  default
                </span>
              )}
            </p>
            <p className="mt-0.5 truncate text-xs text-muted">
              {look.layers.map((l) => l.name).join(" + ")}
            </p>
          </div>
          <div className="flex shrink-0 gap-3 text-xs">
            {!look.isDefault && (
              <button
                type="button"
                className="text-muted hover:text-ink"
                onClick={() =>
                  updateLook.mutate({ lookId: look.lookId, patch: { isDefault: true } })
                }
              >
                Set default
              </button>
            )}
            <button
              type="button"
              className="text-muted hover:text-error"
              onClick={() => deleteLook.mutate(look.lookId)}
            >
              Remove
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
