import { useAccount } from "@/hooks/use-shopper";
import { useSignatureLookMutations, useSignatureLooks } from "@/hooks/use-signature-looks";

export default function ProfileSignatureLooks() {
  const { data: account } = useAccount();
  const { data: looks = [], isLoading } = useSignatureLooks(!!account);
  const { updateLook, deleteLook } = useSignatureLookMutations();

  if (isLoading) return null;

  return (
    <div>
      <p className="eyebrow">Signature Looks</p>

      {looks.length === 0 ? (
        <p className="mt-6 max-w-lg text-[13px] leading-relaxed text-slate">
          No Signature Looks yet. In the studio, dress your avatar in a base outfit you like and
          choose{" "}
          <span className="text-[11px] tracking-[0.14em] text-graphite uppercase">
            Make signature look
          </span>{" "}
          — new garments will then be tried over clothes you actually wear.
        </p>
      ) : (
        <ul className="rule-stack mt-8 border-t border-b border-hairline">
          {looks.map((look) => (
            <li key={look.lookId} className="flex items-center gap-6 py-5">
              <span className="flex size-14 shrink-0 items-center justify-center overflow-hidden rounded-full border border-hairline bg-bone">
                {look.thumbnailUrl ? (
                  <img src={look.thumbnailUrl} alt="" className="size-full object-cover" />
                ) : (
                  <span className="text-[11px] text-slate">
                    {look.name.slice(0, 2).toUpperCase()}
                  </span>
                )}
              </span>

              <div className="min-w-0 flex-1">
                <p className="flex items-baseline gap-3 text-[14px] font-medium text-graphite">
                  {look.name}
                  {look.isDefault && <span className="eyebrow">Default</span>}
                </p>
                <p className="mt-1.5 truncate text-[12px] text-ash">
                  {look.layers.map((l) => l.name).join(" + ")}
                </p>
              </div>

              <div className="flex shrink-0 gap-5 text-[10px] tracking-[0.14em] uppercase">
                {!look.isDefault && (
                  <button
                    type="button"
                    className="text-ash transition-colors hover:text-graphite"
                    onClick={() =>
                      updateLook.mutate({ lookId: look.lookId, patch: { isDefault: true } })
                    }
                  >
                    Set default
                  </button>
                )}
                <button
                  type="button"
                  className="text-ash transition-colors hover:text-error"
                  onClick={() => deleteLook.mutate(look.lookId)}
                >
                  Remove
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
