# MIRRA signup and live-camera correction — design QA

Date: 6 October 2026

## Result

**final result: passed** for the requested UI/auth correction and the explicitly authorized local walkthrough with Redis/CLO off. No actionable P0/P1/P2 finding remains in the inspected UI states.

This result does not certify a completed native avatar pipeline. Physical camera capture and a full live CLO body/face/review/try-on run remain external acceptance checks. The preview labels its example data and does not claim that generation succeeded.

## Source truth and scope

- Selected QR reference: `codex-clipboard-1bb272dd-80d4-4bc8-9370-adb6256628c0.png`, 1548 × 860 pixels, supplied by the user.
- Previous phone UI: `codex-clipboard-89330a1e-10ee-4745-880f-e8188edb8124.png`, 1276 × 1506 pixels.
- Rough review reference: `codex-clipboard-d55cc30a-5f76-48a1-92a5-9ff6d08c38ea.png`, 1446 × 1046 pixels.
- The two supplied flow PDFs were previously read in full. Shopify-dependent work is recorded in `SHOPIFY_DEFERRED.txt`.
- The user's explicit standalone-flow instruction takes precedence over the Profile sidebar in the reference: first signup → QR/camera → sync confirmation → introduction → waiting as needed → measurement review → Studio. Profile is never mounted in this route.
- Returning sign-in opens Studio without checking avatar completeness. Google callback distinguishes actual account creation from returning or linked accounts.
- The references are rough; product copy, camera permissions, supported model inputs and existing backend contracts take precedence over invented SMS delivery or a two-field review.
- This continuation changes onboarding/auth and shopper photo controls. It preserves the existing Profile layout, application colors, merchant work, live catalogue and ordinary Studio backend paths.

Preview: http://localhost:3000/onboarding/qr. The explicit local walkthrough is http://localhost:3000/onboarding/qr?preview=1.

## Evidence and normalization

Evidence directory: `.agent/website-launch-2/onboarding-qa/oct06/`.

| State | Evidence | Verified viewport / image dimensions |
| --- | --- | --- |
| Live QR, final renewed link | `qr-final-viewport.png` | 1548 × 860 |
| Tablet QR | `qr-tablet.png` | 820 × 1000 |
| Mobile QR | `qr-mobile.png` | 390 × 844 |
| Phone details | `phone-details-final.png` | 390 × 844 |
| Front live-camera entry | `camera-front-mobile.png` | 390 × 844 |
| Confirmation tick | `confirmation-mobile.png` | 390 × 844; explicit preview |
| Introduction placeholder | `video-placeholder-mobile.png` | 390 × 844; explicit preview |
| Blurred waiting state | `building-mobile.png` | 390 × 844; explicit preview |
| Desktop measurement review | `review-desktop.png` | 1548 × 884 full-page image; explicit preview |
| Mobile review | `review-mobile-visible.png` | 390 × 844; explicit preview, normal vertical scroll |
| Mobile measurement validation | `review-mobile-validation.png` | 390 × 844; explicit preview |
| Studio handoff | `studio-preview.png`, `studio-preview-mobile.png` | 1548 × 860 and 390 × 844; labelled example figure, real catalogue |

Dimensions were checked from rendered DOM and saved image files. Viewport controls apply to the bound tab; desktop-only captures were not mislabeled as mobile evidence. No fixed iframe is needed for the current captures. Full-page captures are used for composition, not fold-position claims.

Reference and implementation were composed into the same image, then opened for visual review:

- `comparison-qr-full.png`: entire source and implementation, each normalized to 900px width.
- `comparison-qr-type.png`: heading and supporting-copy crops, each normalized to 800px width.
- `comparison-qr-controls.png`: QR panel, text and actions, each normalized to 420px width.
- `comparison-phone.png`: previous desktop capture form and revised phone view, each normalized to 450px width; the different original viewports are intentional and declared.
- `comparison-review.png`: rough review mock and desktop review, each normalized to 900px width; sample figure and measurements are explicitly labelled.

The final desktop QR action and bypass are above the 860px fold; all four pose labels are visible. Tablet and phone QR actions are reachable, phone details/camera entry fit their viewport, and reviewed phone screens have no horizontal overflow. Long mobile review and Studio content scroll normally.

## Findings and iteration history

1. **P1, resolved — returning sign-in was forced into setup.** Removed the completeness-based destination query. Email login goes to Studio; only actual new Google account creation starts signup setup. Safe explicit destinations and product context remain preserved. Frontend routing and backend new/returning/linked-account tests cover this distinction.
2. **P1, resolved — camera buttons opened a file/gallery picker.** All shopper capture controls now use the shared live camera. Front/side body photos and optional face views retain the existing File upload contracts. There is no file-input fallback.
3. **P1, resolved — unavailable workers prevented reviewing later screens.** Added an explicit development/staging-gated preview. Confirmation, placeholder introduction, blurred waiting, example measurement review and Studio preview require no generation jobs or account writes. Authentication and the API/database remain required for the real Studio catalogue.
4. **P2, resolved — QR visual direction differed from the chosen mock.** Restored the cream-clothed four-angle avatar illustration beside a quiet white QR panel. Removed the old three-guide desktop composition, uppercase eyebrows and divider-based capture form. The actual photo requirements remain two body views plus optional face capture.
5. **P2, resolved — pose labels sat at the desktop fold.** Bounded the illustration by viewport height and compacted the QR panel; increased key guidance slightly for readability. The final renewed-code capture keeps both labels and bypass visible.
6. **P2, resolved — programmatic focus outlined the phone heading.** Kept focus transfer for screen readers, suppressed the noninteractive heading outline and retained visible focus treatment on controls.
7. **P2, resolved — camera async cleanup could race.** Stream ownership cancels obsolete permission results, stops tracks on exit/hide/switch and ignores a stale playback rejection after a newer stream opens. Extracted object-URL cleanup into its own hook; lint has no warnings.

## Five quality surfaces

**Typography.** Existing sans-serif controls and restrained serif page headings follow the product language. No uppercase display eyebrow is added. Phone fields use readable sizes; decorative serif text does not enter controls. The mock does not specify an exact licensed font; an exact font match is not claimed.

**Spacing/layout.** Standalone shell, compact QR panel, full-body illustration and four angle labels follow the reference composition while omitting its sidebar as explicitly requested. Phone details, capture and review form discrete steps. There are no decorative divider rules, card outlines or shadows in these onboarding controls. Utilities stay secondary.

**Colors/tokens.** Scoped warm white/cream surfaces, near-black primary actions, warm-grey copy and sage completion markers establish hierarchy. The existing Profile/Studio/global palette was not rethemed. Focus indicators remain functional. Reduced motion disables decorative animation and automatic placeholder cycling.

**Image quality.** Full figures are retained in the four-angle illustration. Practical front/side/face guides stay consistent. Loading uses an intentionally blurred example, and preview review/Studio explicitly label illustrations. Real review still uses the existing GLB viewer and face attachment; illustration QA cannot certify body/face reconstruction quality.

**Copy/content.** QR actions work: copy the link, open this device's camera flow, or renew the code. SMS delivery is not fabricated. Localhost/HTTPS guidance is confined to the local environment. The phone page asks for required height before live front/side photos; weight and face capture remain optional. Available model measurements are reviewed rather than copying the mock's two illustrative sliders. The final introduction is visibly a placeholder.

## Interaction and technical verification

- Actual public token link opens without another sign-in. Browser inspection confirms zero `input[type=file]` controls on the capture page; source search confirms none in shopper capture/Profile photo paths.
- Opening the live camera reached the browser permission request. Permission remained pending in this test environment; a physical camera frame was not claimed. Back remains usable. Unit tests cover obsolete grants/rejections, stream cleanup, unavailable/low-resolution video, full-frame JPEG export and error guidance.
- Camera previews support a five-second body timer, cancellation, flipping, retake and confirmation. The unmirrored full sensor frame is submitted through the existing body/face APIs.
- Preview sequence was exercised through Studio at desktop and 390px widths. Studio loaded existing API catalogue products and kept unavailable commerce fields honest. Ordinary close was also exercised: it opened `/studio`, with its avatar-creation prompt, without a forced setup redirect or landing-page detour.
- Review: 175cm converts to 68.9in and back; edited waist is accepted; 12cm height produces a clear supported-range error and blocks navigation. Correcting the value permits the Studio handoff.
- 62 frontend tests pass. Final typecheck, lint (zero warnings), production build and `git diff --check` pass. The existing approximately 996kB GLB-viewer bundle warning remains.
- 148 backend/model tests pass, including new Google-account routing coverage. The existing Starlette/httpx deprecation warning remains.
- Earlier native BMnet and face-model smoke checks remain documented in the archived 5 October QA. They are not evidence of a completed CLO body run.
- Inspected browser logs contain development connection/hot-update messages and no new application rendering exception. Expected processing-queue failures remain recoverable live-flow states.

## Remaining external acceptance

- Use phone-reachable frontend AND API HTTPS; verify OS/browser permission and physical front/side/face capture and sync.
- Run Redis/workers and the native CLO/plugin environment, provide the missing female base AVT, and verify actual body/face alignment, corrected measurement rebuild and live Studio try-on.
- Supply the approved introduction video and captions; `VITE_ONBOARDING_VIDEO_URL` is the integration point.
- Disable the staging preview flag for production; `ONBOARDING_PREVIEW.md` records behavior and removal steps. Camera-only UI is not a server-verified liveness/identity guarantee.
- Connect and validate Shopify once a real store is available; exact deferrals remain in `SHOPIFY_DEFERRED.txt`.

The historical 5 October report is retained as `design-qa-2026-10-05.md` in this evidence directory.
