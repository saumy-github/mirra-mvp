import { useEffect, useRef, useState } from "react";
import { ArrowRight, Plus, X } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useAccount } from "@/hooks/use-shopper";
import { useSignatureLookMutations, useSignatureLooks } from "@/hooks/use-signature-looks";
import type { SignatureLook } from "@/integrations/mirra-api/types";

const EDITORIAL_IMAGES = [
  "/profile/signature-everyday.jpg",
  "/profile/signature-work.jpg",
  "/profile/signature-evening.jpg",
];

const CURATED_FALLBACKS = [
  {
    name: "Everyday",
    description: "Clean, comfortable, and effortless.",
    image: EDITORIAL_IMAGES[0],
  },
  {
    name: "Work",
    description: "Polished layers for focus and impact.",
    image: EDITORIAL_IMAGES[1],
  },
  {
    name: "Evening",
    description: "Elevated pieces for after dark.",
    image: EDITORIAL_IMAGES[2],
  },
];

type LookCard = {
  look: SignatureLook | null;
  name: string;
  description: string;
  image: string | null;
  isDefault: boolean;
  isTemplate: boolean;
};

export default function ProfileSignatureLooks() {
  const navigate = useNavigate();
  const { data: account } = useAccount();
  const { data: looks = [], isLoading } = useSignatureLooks(!!account);
  const { createLook, updateLook, deleteLook } = useSignatureLookMutations();
  const [editing, setEditing] = useState<SignatureLook | null>(null);
  const [editName, setEditName] = useState("");
  const [editDefault, setEditDefault] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const editTriggerRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (editing && dialogRef.current && !dialogRef.current.open) {
      dialogRef.current.showModal();
    }
  }, [editing]);

  if (isLoading) return <SignatureLooksLoading />;

  const cards: LookCard[] = looks.length
    ? looks.map((look) => ({
        look,
        name: look.name,
        description:
          look.layers.length > 0
            ? look.layers.map((layer) => layer.name).join(" · ")
            : "A saved foundation for your studio.",
        image: look.thumbnailUrl,
        isDefault: look.isDefault,
        isTemplate: false,
      }))
    : CURATED_FALLBACKS.map((look) => ({
        ...look,
        look: null,
        isDefault: false,
        isTemplate: true,
      }));

  function openEditor(look: SignatureLook, trigger: HTMLButtonElement) {
    updateLook.reset();
    deleteLook.reset();
    editTriggerRef.current = trigger;
    setEditing(look);
    setEditName(look.name);
    setEditDefault(look.isDefault);
  }

  function closeEditor() {
    if (dialogRef.current?.open) {
      dialogRef.current.close();
      return;
    }

    setEditing(null);
  }

  function duplicate(look: SignatureLook) {
    if (createLook.isPending) return;

    createLook.mutate({
      name: `${look.name} copy`,
      layers: look.layers,
      avatarProfileVersion: look.avatarProfileVersion,
      thumbnailUrl: look.thumbnailUrl,
      isDefault: false,
    });
  }

  const editorBusy = updateLook.isPending || deleteLook.isPending;

  return (
    <div className="profile-looks-page">
      <div className="profile-looks-layout">
        <section className="profile-looks-intro" aria-labelledby="signature-looks-title">
          <h1 id="signature-looks-title">
            Signature
            <br />
            looks
          </h1>
          <p>
            Create and curate your default foundations. These looks show up in the studio when
            building outfits.
          </p>
          <Link to="/studio" className="profile-dark-button profile-looks-create">
            <Plus aria-hidden size={20} strokeWidth={1.8} />
            Create signature look
          </Link>
        </section>

        <div
          className="profile-looks-cards"
          role="list"
          aria-label={looks.length ? "Saved signature looks" : "Signature look templates"}
        >
          {cards.map((card) => {
            const look = card.look;

            return (
              <article
                className="profile-look-card"
                key={look?.lookId ?? card.name}
                role="listitem"
              >
                <div className="profile-look-card__image">
                  {card.image ? (
                    <img
                      src={card.image}
                      alt={
                        card.isTemplate
                          ? `${card.name} editorial template preview`
                          : `${card.name} signature outfit`
                      }
                    />
                  ) : (
                    <div
                      className="profile-look-card__placeholder"
                      role="img"
                      aria-label={`${card.name} has no preview image`}
                    >
                      <span className="profile-look-card__placeholder-mark" aria-hidden>
                        {card.name.slice(0, 2)}
                      </span>
                      <span className="profile-look-card__placeholder-copy">
                        Preview not available
                      </span>
                    </div>
                  )}
                  {(card.isTemplate || card.isDefault) && (
                    <span className="profile-look-card__badge">
                      {card.isTemplate ? "Template preview" : "Default"}
                    </span>
                  )}
                </div>
                <div className="profile-look-card__body">
                  <div>
                    <h2>{card.name}</h2>
                    <p>{card.description}</p>
                  </div>
                  {look ? (
                    <div className="profile-look-card__actions">
                      <button
                        type="button"
                        onClick={(event) => openEditor(look, event.currentTarget)}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        disabled={createLook.isPending}
                        onClick={() => duplicate(look)}
                      >
                        {createLook.isPending ? "Copying…" : "Duplicate"}
                      </button>
                      <button
                        type="button"
                        className="profile-look-card__studio"
                        onClick={() =>
                          navigate("/studio", { state: { signatureLookId: look.lookId } })
                        }
                      >
                        Open studio <ArrowRight aria-hidden size={16} strokeWidth={1.7} />
                      </button>
                    </div>
                  ) : (
                    <div className="profile-look-card__actions profile-look-card__actions--template">
                      <span className="profile-look-card__template-label">Inspiration only</span>
                      <button
                        type="button"
                        className="profile-look-card__studio"
                        onClick={() => navigate("/studio")}
                      >
                        Build in studio <ArrowRight aria-hidden size={16} strokeWidth={1.7} />
                      </button>
                    </div>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      </div>

      <p className="profile-looks-note">
        {looks.length
          ? "Looks are used as a starting point in the studio and can be mixed, matched, and refined."
          : "Template previews are inspiration. Start in the studio to create and save your own look."}
      </p>

      {createLook.error && (
        <p className="profile-inline-error" role="alert">
          {createLook.error instanceof Error
            ? createLook.error.message
            : "The look was not copied."}
        </p>
      )}

      {editing && (
        <dialog
          ref={dialogRef}
          className="profile-dialog-backdrop"
          aria-labelledby="edit-look-title"
          onCancel={(event) => {
            if (editorBusy) event.preventDefault();
          }}
          onClose={() => {
            setEditing(null);
            editTriggerRef.current?.focus();
          }}
          onClick={(event) => {
            if (event.target === event.currentTarget && !editorBusy) closeEditor();
          }}
        >
          <section className="profile-look-dialog" onClick={(event) => event.stopPropagation()}>
            <button
              type="button"
              className="profile-dialog-close"
              aria-label="Close edit look dialog"
              disabled={editorBusy}
              onClick={closeEditor}
            >
              <X aria-hidden size={18} />
            </button>
            <p className="profile-meta">Signature look</p>
            <h2 id="edit-look-title">Edit look</h2>
            <form
              aria-busy={editorBusy}
              onSubmit={(event) => {
                event.preventDefault();
                if (editorBusy) return;

                deleteLook.reset();
                updateLook.mutate(
                  {
                    lookId: editing.lookId,
                    patch: { name: editName.trim() || editing.name, isDefault: editDefault },
                  },
                  { onSuccess: closeEditor },
                );
              }}
            >
              <label htmlFor="signature-look-name">Name</label>
              <input
                id="signature-look-name"
                value={editName}
                onChange={(event) => setEditName(event.target.value)}
                maxLength={80}
                disabled={editorBusy}
                autoFocus
              />
              <label className="profile-look-dialog__check">
                <input
                  type="checkbox"
                  checked={editDefault}
                  onChange={(event) => setEditDefault(event.target.checked)}
                  disabled={editorBusy}
                />
                Use as my default look
              </label>
              {(updateLook.error || deleteLook.error) && (
                <p className="profile-inline-error" role="alert">
                  {deleteLook.error
                    ? "The look could not be removed. Please try again."
                    : "The look could not be updated. Please try again."}
                </p>
              )}
              <div className="profile-look-dialog__actions">
                <button
                  type="button"
                  className="profile-look-dialog__remove"
                  disabled={editorBusy}
                  onClick={() => {
                    if (editorBusy) return;
                    updateLook.reset();
                    deleteLook.mutate(editing.lookId, { onSuccess: closeEditor });
                  }}
                >
                  {deleteLook.isPending ? "Removing…" : "Remove look"}
                </button>
                <button type="submit" className="profile-dark-button" disabled={editorBusy}>
                  {updateLook.isPending ? "Saving…" : "Save changes"}
                </button>
              </div>
            </form>
          </section>
        </dialog>
      )}
    </div>
  );
}

function SignatureLooksLoading() {
  return (
    <div className="profile-looks-page profile-page-loading" aria-busy="true" role="status">
      <div className="profile-looks-layout" aria-hidden>
        <div className="profile-loading-copy profile-loading-copy--looks">
          <span className="profile-loading-block profile-loading-block--title" />
          <span className="profile-loading-block profile-loading-block--copy" />
          <span className="profile-loading-block profile-loading-block--action" />
        </div>
        <div className="profile-loading-cards">
          {Array.from({ length: 3 }, (_, index) => (
            <span className="profile-loading-block profile-loading-block--look" key={index} />
          ))}
        </div>
      </div>
      <span className="sr-only">Loading your saved looks…</span>
    </div>
  );
}
