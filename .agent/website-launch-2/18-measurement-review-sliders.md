# Measurement review adjustments

Updated 8 October 2026.

## Change

Added shared slider controls to the standalone signup review and the existing Profile photo-measurement review. Each supported baseline measurement can be adjusted with a slider or exact numeric entry. Changes are identified with a subtle surface tint and their starting value, with per-field and full reset controls.

Draft values remain metric while switching display units. Slider changes use 0.1 cm / kg increments; exact numeric entry preserves finer decimals. Untouched fields are omitted from the correction payload and preserve their measured precision. The UI validates existing supported ranges and locks controls during confirmation.

## Existing backend integration

Standalone confirmation continues to call `POST /api/v1/photo-measurements/setup/{pairingId}/review`. Corrections are persisted to `user_measurements`, copied into the new avatar job's `measurement_snapshot`, and applied before the flow opens Studio. An unchanged baseline skips the additional build. Initial avatar preview generation still precedes this review, as in the existing setup flow.

Profile capture review continues to call `POST /api/v1/photo-measurements/{captureId}/apply`, preserving warnings, retake, and the existing saved-profile callback.

The review supports the nine fields already accepted by the live contract. Neck length is not supported; raw model neck circumference is not a live contract field either. No backend schema or native reconstruction behavior was changed.

## Verification

- 22 frontend tests passed, including correction precision, imperial conversion, unit-switch stability, resetting, optional weight, validation, existing post-auth routing and HTTP provider tests.
- All 34 photo-measurement backend tests passed. A new integration test verifies 0.01 cm corrections reach the avatar snapshot while other baseline values survive; repeated setup advancement does not overwrite edits or enqueue duplicates.
- TypeScript check and lint for changed TS/TSX files passed.
- Production build passed; Vite still reports the existing large avatar-viewer chunk advisory.
- Browser review verified keyboard slider increments, exact entry, unit switching, reset and refusal of invalid confirmation.
- Mobile review at 390 × 844 has no horizontal overflow and gives sliders 44 px touch height.
- Preview confirmation navigated to `/studio?setupPreview=1`; the unauthenticated browser then reached the existing login guard. An authenticated live Studio/reconstruction run was not performed.

Screenshots: `onboarding-qa/oct08-measurement-review/desktop-review.png` and `mobile-review.png` (clearly labeled example previews).

Native CLO/Redis remain outside this local preview verification. Run the live workers and reconstruction infrastructure for the physical-phone-to-final-avatar check described in `ONBOARDING_PREVIEW.md`.
