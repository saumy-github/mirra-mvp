# Temporary onboarding preview

Updated 8 October 2026.

## Use it while Redis and CLO are off

1. Open the signup QR page and choose **Skip for now · preview next steps** beneath the QR.
2. Alternatively, open `http://localhost:3000/onboarding/qr?preview=1` directly.
3. The walkthrough shows the confirmation tick, an introduction video placeholder, the blurred build screen, and a review of clearly marked example measurements.
4. Choose **Open Studio**. Studio opens in preview mode with an example figure and the real catalogue. It does not require Redis or CLO. Authentication and the API/database are still required for the real Studio catalogue.

The walkthrough does not upload photos, enqueue model jobs, create an avatar, change measurements, or mark the real onboarding session complete. It does not replace or clear the shopper's existing avatar. Preview changes are held in component state and discarded. Studio preview uses `setupPreview=1` to suppress avatar/try-on jobs; it labels the example figure. **Return to setup** resumes the real flow. Removing the query parameter restores the ordinary Studio.

Availability: automatically enabled by Vite's development mode. Production builds keep it off unless `VITE_ENABLE_ONBOARDING_PREVIEW=true` is explicitly set at build time for staging. This flag is a UI preview switch, not a backend authentication bypass. Remove the staging flag before release. The preview link is also available on setup load/build errors, so an unavailable worker cannot hide it.

## Signup and sign-in

- New email signup starts the standalone QR flow.
- First Google account creation starts it too; the backend returns `newAccount=1` only when it actually creates the account.
- Returning password/Google sign-in opens Studio (or an explicitly requested Profile route). An incomplete avatar no longer causes an automatic QR redirect.
- A returning user can explicitly open avatar setup from Studio or Profile.
- Closing setup opens Studio, never the landing page. Onboarding never mounts the Profile sidebar.

## Live camera

The phone link now guides the user through details, a front body photo, a side body photo, then an optional face photo. Optional turned face views remain available. Every shopper photo control uses `navigator.mediaDevices.getUserMedia`; there are no file inputs or gallery choices in the capture, measurement, or face forms.

The camera supports a five-second body-photo timer, flipping cameras where available, preview, retake and confirmation. It exports the full sensor frame as JPEG and submits it through the existing photo/face APIs. Tracks stop on retake, leaving the camera screen, switching cameras, and hiding the browser tab. A permission request resolving after exit is immediately stopped. Permission denial, missing/busy cameras, low resolution and insecure origins have recovery messages without a file-upload fallback.

Camera access needs HTTPS or localhost and browser/OS permission. A phone cannot reach the computer's `localhost`; both frontend and API must use phone-reachable HTTPS, with the API URL/CORS/cookie settings configured accordingly. `VITE_CAPTURE_ORIGIN` only changes the QR's frontend origin; it does not create a tunnel or make a localhost API reachable.

Camera-only capture is not identity verification or a liveness guarantee. Browser clients, virtual cameras and direct API requests can still be spoofed. Server-verified liveness/anti-replay checks would be separate work; they were not added or claimed by this UI change.

## Video placeholder and real processing

`VITE_ONBOARDING_VIDEO_URL` is blank for now. The placeholder cycles three short product captions, then advances; **Continue preview** / **Skip introduction** is always available. With reduced motion, automatic cycling stops and the user continues manually. Set a public video URL once the final introduction is supplied; the player has native controls, muted autoplay and an end transition. Prepare captions/transcript with the final asset.

The live flow remains driven by the existing measurement, face and CLO job states. Finishing the tour does not fabricate a ready avatar. Actual review still uses model results and sends corrections through the backend. Corrected measurements rebuild the real avatar before Studio opens. The temporary preview is the only path with timed example states.

## Measurement review

The review now provides sliders and exact numeric entry for every available supported measurement: height, weight, shoulder width, chest, waist, hips, inseam, and bust/under-bust when present. Missing weight remains optional. The same controls are used when reviewing a new photo measurement from Profile.

- Sliders move in 0.1 cm / kg increments, with equivalent increments in inches / pounds. Exact entry retains finer decimals.
- A changed row receives a subtle green tint, shows its starting value, and offers a reset. **Reset all** restores the original baseline.
- Unit switching changes the display only. Draft corrections stay in metric units, so repeated switches do not accumulate rounding error. Untouched baseline values retain their original precision.
- Confirmation validates the supported ranges and sends only changed fields through the existing review API. Controls are disabled while saving.

The existing live sequence is preserved: model measurements → initial avatar preview → review → corrected avatar rebuild when needed → Studio. Corrections are saved to `user_measurements` and included in the new avatar job's `measurement_snapshot`. The flow waits for that job before opening Studio. Confirming an unchanged baseline does not create another build. Profile review continues to use the existing capture-apply endpoint.

Neck length is not part of the current profile/CLO field contract. The model's raw neck output represents circumference and is not currently mapped into that contract either. Adding either field would require an explicit model-to-profile-to-CLO mapping; this UI does not invent an unsupported slider. Fine control increments also do not imply a guarantee of model accuracy.

The local preview includes these controls with example data and still saves nothing. Live camera → model → corrected CLO reconstruction requires the workers and CLO infrastructure listed below.

## Before release

- Supply the final introduction video and captions.
- Run Redis, workers and CLO/plugin infrastructure; provide the missing female base AVT.
- Verify physical phone front/side/face capture, sync, actual reconstruction, measurement review and live try-on end to end over HTTPS.
- Disable the preview flag for production. Shopify-dependent work remains listed separately in `SHOPIFY_DEFERRED.txt`.
