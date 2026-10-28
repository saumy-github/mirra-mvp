# Standalone shopper onboarding

5 October 2026; corrected 6 October 2026

## Implemented

Signup → standalone QR → phone body/face capture → sync confirmation → introduction placeholder (final video pending) while trained measurement, facial reconstruction and CLO jobs run → blurred waiting state if necessary → review all available measurements → Studio.

The shopper route never opens Profile. Returning sign-in opens Studio without checking avatar completeness or forcing setup. A first Google account is distinguished from an existing or linked account by the backend callback. Explicitly opening setup still resumes its server state. Manual measurements remain available. The simple close control opens Studio.

The orchestration record uses the existing capture, measurements, faces and avatar services. Phone completion and measurement-worker completion can each advance the same setup; an atomic claim prevents ordinary duplicate job starts. Review corrections create a fresh real body job before completion. Failure, face skip/retake, stale-session rejection and renewed phone links are handled explicitly. This is not a timer-driven simulated avatar build.

The frontend-only QA fixtures under `website/frontend/tests/` remain isolated development entries. On 6 October the user also authorized an explicit, development-gated walkthrough while Redis/CLO are unavailable. `/onboarding/qr?preview=1` shows confirmation → video placeholder → waiting → example review → Studio preview. It never writes profile data or creates jobs. See `ONBOARDING_PREVIEW.md` for the entry points, flags, limitations and removal steps.

## Preservation

This work was added on top of an already-dirty checkout containing photo/face integration, merchant linking, measurement contract, worker and Profile changes. Those changes were retained. The native model/runtime contracts were reused. A real WebP decode mismatch in the photo pipeline was fixed: accepted browser WebP uploads now decode through OpenCV into the MediaPipe image path.

The Profile sidebar and application-wide colors were not redesigned in this continuation. Existing Profile measurement editing and avatar management remain connected. Shopper photo fields now use a shared live camera instead of file/gallery pickers, including Profile's body and face forms. The token-scoped phone page uses a short camera wizard with the same upload contracts.

## Studio screenshot investigation

The earlier “Price unavailable”, “Commerce pricing has not been connected for this piece yet”, and “Your 3D avatar isn't available” UI is attributed by Git to commit `a8602c73`, 8 September 2026, author `MadhavanPS` (`Update merchant digitization pipeline, studio components, auth flows, and worker tasks`). This identifies the recorded commit author, not necessarily the individual who typed every line.

The avatar branch still calls `getRuntimeProvider().getAvatarGlb()`; it is a failure/empty presentation around a backend request. Its presence alone does not establish why that user's GLB was missing. Catalogue data also still comes from the live runtime provider. A missing Shopify commerce connection explains unavailable commerce fields but does not replace the avatar backend. This continuation preserves those calls.

## Verified and blocked

- Browser: standalone entry, live expiring QR, signed-out phone page, camera permission request, recoverable live queue errors, ordinary close to Studio, full review fields, unit conversion, invalid-height recovery and desktop/tablet/phone layouts. The explicit preview was exercised through Studio at desktop and phone widths, with the real catalogue and a labelled example figure. A physical camera frame and native CLO run remain unverified.
- Frontend: 62 tests, lint (zero warnings), typecheck and production build pass. Existing 3D chunk-size warning remains.
- Final backend/model regression suite: 148 tests pass, with the existing Starlette/httpx deprecation warning. Details and visual evidence are in `design-qa.md`.
- Actual trained BMnet smoke: returned measurement fields without warnings using generated guide images.
- Actual face smoke: generated a 1,151,940-byte GLB without warnings from the generated face example.
- A full native CLO run was not verified. The local API returned a real processing queue failure; native CLO worker/plugin operation is still required. The female base AVT is absent. No fake ready state was added to work around these limitations.
- A physical phone needs phone-reachable frontend/backend HTTPS configuration, not the laptop's localhost URL. `VITE_CAPTURE_ORIGIN` is documented for that deployment.

The supplied merchant PDF also describes human sales/approval and external payment/support operations. Existing merchant workspace and garment APIs were preserved; unsupported payment/Jira/store actions were not fabricated. See `SHOPIFY_DEFERRED.txt` for exact follow-up dependencies.
