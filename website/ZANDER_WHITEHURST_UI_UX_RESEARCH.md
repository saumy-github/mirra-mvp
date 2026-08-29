# Post-login UI/UX research and implementation brief

Research source: [Zander Whitehurst on Instagram](https://www.instagram.com/zanderwhitehurst/)

Research date: 26 August 2026

Scope: the first 20 items shown on the profile's Reels tab: the three pinned reels followed by the newest 17 reels. This brief applies the findings only to Mirra's authenticated product experience. Public marketing routes and pre-login authentication screens are explicitly out of scope.

## Executive summary

The reels share one consistent thesis: a polished interface is not made by adding decoration. It is made by reducing the effort required to understand status, choose a next step, and recover from uncertainty.

The most transferable principles are:

1. Give each view one obvious primary task and action.
2. Build hierarchy with type scale, alignment, whitespace, and semantic status cues before adding containers, borders, or colour.
3. Reserve surfaces and colour for emphasis; do not make every group look equally important.
4. Make forms feel progressive: preserve labels, supply useful defaults, format input, validate immediately, and use the right mobile keyboard.
5. Treat motion as a reusable part of the component system. Motion should explain a state change, preserve spatial context, and respect reduced-motion preferences.
6. Keep design components and code components aligned through the same orthogonal properties, tokens, and state names.
7. Prefer a coherent icon family over custom-drawing ordinary interface symbols.
8. Simplify only after identifying the user's real task. Do not remove accessibility labels, edge-case context, or decision-critical information in pursuit of visual minimalism.

For Mirra, these ideas translate most directly to the measurement intake, Studio, and Profile surfaces. The implementation deliberately avoids the public marketing website, global route styling, and pre-login screens.

## Research method

Each reel was played in the signed-in Instagram interface and sampled across multiple moments rather than judged from its thumbnail or post caption. The review combined:

- the before-state, editing sequence, and after-state shown on screen;
- the creator's synchronized on-screen narration captions and the published reel description;
- the ordering, pacing, zooms, arrows, success/error marks, and other visual cues used to explain each change;
- visible audience objections where they exposed accessibility or task-model risks in the recommendation.

The audio/visual pattern is remarkably consistent. A short spoken hook names a mistake, the reel isolates one visual symptom, the edit demonstrates one rule at a time, and the reveal resolves into a compact after-state. Short clauses and synchronized captions keep the narration scannable without competing with the UI being demonstrated. Reaction shots and rapid zooms are useful for the creator's storytelling, but they are not themselves product-design recommendations.

### Cross-reel audio and visual grammar

The sampled reels ranged from quick, roughly ten-second demonstrations to tutorials of about fifty seconds. Every item was presented as “Original audio.” The analysis used the audible tutorial track together with its synchronized captions and the changing interface frames; it did not treat the caption text as a substitute for watching the design operation.

The recurring editorial structure has four beats:

1. **Imperative hook.** A short “stop doing this” or “try this” statement creates a single design question before the viewer has to parse the screen.
2. **Visual diagnosis.** The before-state is held long enough to see one dominant problem—excess colour, fragmented alignment, duplicated containers, weak hierarchy, or a laborious form.
3. **Clause-to-action synchronization.** Each spoken clause coincides with one visible edit: neutralizing a surface, moving an anchor, changing a component property, formatting input, or adding a status cue. This makes the reason and the manipulation feel causally connected.
4. **Resolved reveal.** The voiceover becomes conclusive as the after-state is shown. Check marks, zoom-outs, or a side-by-side comparison provide punctuation rather than carrying the explanation alone.

The voiceover is direct, compressed, and confident. It generally names the symptom before the technique, which keeps the demonstration outcome-led. On-screen captions arrive in short thought units near—but not on top of—the active design area, allowing the interface to remain the primary evidence. Cuts and zooms align with changes in the spoken argument, so pacing communicates hierarchy: the important transformation gets more screen time than cursor travel or setup.

The product-design lesson is not to copy the reels' social-video energy into Mirra. It is to preserve causality and focus: one status change, one corresponding visual response, and one clear next action. Product motion should be quieter and interruptible, with reduced-motion equivalents; sound should not be required to understand an application state.

## Reel-by-reel analysis

### 1. Stop designing custom icons

[Reel](https://www.instagram.com/zanderwhitehurst/reel/DABHlSOASqt/)

- Visual execution: a hand-built home icon is shown under construction, then the reel cuts to complete icon libraries including Heroicons, Hugeicons, and Lucide.
- Narration argument: ordinary system icons are infrastructure, not a place to spend product-design time.
- Transferable lesson: pick one well-drawn family, standardize size/stroke/optical alignment, and reserve custom icons for genuinely proprietary concepts.
- Mirra implication: keep app navigation and status symbols from one family; do not mix decorative, filled, and thin-line styles without a semantic reason.

### 2. Stop adding colours to your UI

[Reel](https://www.instagram.com/zanderwhitehurst/reel/C7yo_TjtaX_/)

- Before: a mobile service app uses a saturated blue canvas, several category colours, dark blue panels, pink actions, and a coloured avatar at the same time.
- Transformation: major areas are neutralized while the circular primary action and tiny notification/status details retain colour.
- After: white and warm-neutral surfaces create breathing room; colour identifies the next action or exceptional state.
- Mirra implication: the authenticated app should use neutrals for structure and reserve accent/success/error colours for meaning.

### 3. Stop adding backgrounds to UI cards

[Reel](https://www.instagram.com/zanderwhitehurst/reel/C5QeamHtT44/)

- Before: image, metadata, and price are wrapped in a conventional card surface.
- Transformation: the media remains visually bounded, while the text sits directly in the page flow and whitespace performs the grouping.
- Strong use case: product, travel, and editorial tiles whose media already supplies a clear boundary.
- Guardrail: a surface is still appropriate when contrast, selection, density, or interaction affordance requires it.

### 4. Stop centring text in your UI

[Reel](https://www.instagram.com/zanderwhitehurst/reel/DcN2nJEu9L2/)

- Before: product name, subtitle, price/legal text, and CTA create several centered anchors.
- After: title and supporting text share a left anchor, the media gets more visual weight, and the compact action sits in a predictable corner.
- Additional result: the same structure works coherently in light and dark modes.
- Mirra implication: use a single reading edge for multi-line content; reserve centered text for short, intentionally focal states.

### 5. Stop designing UI forms like this

[Reel](https://www.instagram.com/zanderwhitehurst/reel/Db8J5z5Oy8-/)

- Before: a long bank form presents every field, repeated outer labels, hard rectangles, and one distant Continue button.
- After: rounded fields, sensible preselection, live formatting, a focused numeric keyboard, a thumb-reachable forward action, and clear red/green validation states make the task feel progressive.
- Strongest principles: reduce required decisions, prefill known values, use input-specific keyboards, format structured values as they are entered, confirm valid progress immediately, and keep the next action visually stable.
- Accessibility correction: the visual example sometimes relies on placeholder-like text. Mirra must retain a persistent programmatic and visible label; placeholder text must never be the only label.

### 6. Stop treating animation as an afterthought

[Reel](https://www.instagram.com/zanderwhitehurst/reel/Db2zNo2OdL2/)

- Argument: adding unrelated interactions layer-by-layer at the end creates inconsistent motion and duplicated work.
- Visual execution: one systematic instruction is applied across an existing site, followed by a pass/fail reveal.
- Mirra implication: define a small shared motion vocabulary for entrance, selection, state transition, and disclosure; never animate simply because a layer exists.

### 7. Anyone can generate a UI with AI

[Reel](https://www.instagram.com/zanderwhitehurst/reel/DbssmP6oF3p/)

- Before: a balance card contains values but communicates no meaning beyond the numbers; text contrast is weak.
- After: “Project balance” labels the hero value, a green-dot status pill explains availability, secondary figures sit on a clean alignment grid, and the primary action remains obvious.
- Mirra implication: every async or data-heavy state should answer what the value is, what it means, and what the user can do next.

### 8. Stop adding containers to your UI

[Reel](https://www.instagram.com/zanderwhitehurst/reel/DblH1vdIhIT/)

- Before: a profile card uses a panel, divider, button containers, and nested sections to create every group.
- Transformation: spacing first establishes identity, statistics, and actions; a selective tinted band then emphasizes the statistics.
- Mirra implication: begin with content groups and vertical rhythm. Add a surface only where it changes emphasis or interaction.

### 9. Stop adding borders to your UI

[Reel](https://www.instagram.com/zanderwhitehurst/reel/DbDaptQscRR/)

- Before: a two-row score card resembles a small spreadsheet because every row and column is ruled.
- After: alignment, weight, flags, and a selective winner/status treatment communicate the result without a full grid.
- Guardrail: dense comparison tables can still need row separators or zebra surfaces. The rule is to avoid borders that carry no information, not to ban boundaries.

### 10. Stop prototyping without your design system

[Reel](https://www.instagram.com/zanderwhitehurst/reel/DbAzXu3uIh2/)

- Visual execution: an AI-generated dashboard is reconciled with a real system's colour, neutral, navigation, and component foundations.
- Argument: fast prototypes that ignore the system create cleanup rather than acceleration.
- Mirra implication: use authenticated-app semantic tokens and existing components; do not create one-off values for each page.

### 11. Free icon libraries

[Reel](https://www.instagram.com/zanderwhitehurst/reel/DacwJnqOrqB/)

- Visual execution: animated, accessibility-oriented, and dimensional libraries are shown as alternatives to drawing routine assets from scratch; visible examples include animate-ui.com and 3dicons.co.
- Lesson: choose the library to match the interface's semantic and dimensional style. Novelty is not consistency.
- Mirra implication: dimensional icons belong in illustration/empty-state contexts, while navigation and controls should stay in one restrained system set.

### 12. Stop designing components without code

[Reel](https://www.instagram.com/zanderwhitehurst/reel/DaP8QPHIJZq/)

- Before: a button component explodes into many visually enumerated variants.
- Transformation: variant, tone, and size become independent properties and map directly to a code API.
- Mirra implication: component properties should describe orthogonal decisions. Names and states in design should match TypeScript props and application state.

### 13. Animating buttons in Figma Motion

[Reel](https://www.instagram.com/zanderwhitehurst/reel/DaNSI-JOg-8/)

- Visual execution: button/progress elements are animated on a timeline using custom easing; the reel exposes a cubic-bezier curve rather than a generic fade.
- Lesson: good micro-motion has acceleration and intent. Press, selection, progress, and completion should not all use the same animation.
- Mirra implication: preserve spring/curve consistency, keep feedback immediate, and provide near-instant reduced-motion alternatives.

### 14. Figma Motion is finally here

[Reel](https://www.instagram.com/zanderwhitehurst/reel/DaAoPwQoA4-/)

- Visual execution: a profile component is previewed on-canvas with keyframed property changes; animations can be copied and pasted rather than recreated.
- Lesson: motion belongs to the component/state system and needs a reusable handoff, just like colour or spacing.
- Mirra implication: selection indicators, disclosures, and status changes should reuse named motion presets.

### 15. Framer agents for professional UI work

[Reel](https://www.instagram.com/zanderwhitehurst/reel/DZ94Mp0oqY1/)

- Demonstrated patterns: sticky navigation, staggered text, sticky scroll sections, and responsive adaptation.
- Lesson for an application: persistent navigation and preserved spatial context reduce re-orientation; stagger should express hierarchy, not delay access.
- Mirra implication: app chrome should remain stable while page content changes, and mobile layouts must reorganize rather than merely shrink.

### 16. Stop mixing modes in your UI

[Reel](https://www.instagram.com/zanderwhitehurst/reel/DY4LiGiIloa/)

- Before: dark product imagery is joined to a bright white metadata panel inside an otherwise dark catalogue, creating an accidental split component.
- After: imagery, product copy, swatches, and actions share one coherent dark surface and contrast model.
- Mirra implication: do not mix light and dark surfaces inside one functional region unless the boundary itself communicates a state or mode change.

### 17. Add liquid gradients to your UI

[Reel](https://www.instagram.com/zanderwhitehurst/reel/DYRsHy-oNiL/)

- Visual execution: a multi-colour wave gradient is tuned by seed, speed, frequency, angle, amplitude, softness, and blend.
- Useful role: atmospheric depth behind a focal object or branded moment.
- Guardrail: animated gradients should not sit behind dense copy or forms, must keep contrast stable, and must stop or simplify under reduced-motion/transparency settings.
- Mirra implication: if used, this belongs around the avatar/stage—not throughout the application.

### 18. Stop adding content to your UI

[Reel](https://www.instagram.com/zanderwhitehurst/reel/DYMhapEoAHC/)

- Before: an event card contains competition, date, venue, full team names, and two actions.
- Transformation: visual hierarchy is tightened around the event and next action.
- Critical audience correction: some removed content explained the ticket journey. Minimal content is only better if the user's question is still answered.
- Mirra implication: move secondary product and profile information into disclosure, but retain decision-critical fit, availability, error, privacy, and recovery details.

### 19. Stop guessing your UI layout

[Reel](https://www.instagram.com/zanderwhitehurst/reel/DX9RVypIHGi/)

- Before: a run summary gives title and three metrics nearly equal emphasis.
- After: one hero metric gets the largest scale, a “New PB” status explains why it matters, secondary metrics form a row, and the map becomes tertiary context.
- Critical audience correction: the hero metric must come from user/task evidence, not designer preference.
- Mirra implication: measurement completion, fit confidence, and try-on status can be heroes only when they are the immediate task's most useful signal.

### 20. Better UI is not merely “nicer”

[Reel](https://www.instagram.com/zanderwhitehurst/reel/DXrDg7AiHuN/)

- Demonstrated changes: reduce indiscriminate accent colour, clarify grouping, make the decision/action obvious, improve readability, and use spacing for subtle structure.
- Form lesson: related origin/destination values can share a group, while dates and passengers remain separate decisions.
- Critical audience correction: compact date labels and collapsed fields must still handle different months/years, reveal their interaction, and preserve cognitive/accessibility labels.
- Mirra implication: simplify the visible path without compressing away input meaning or edge cases.

## Consolidated design system guidance

### Hierarchy

- Start every screen by naming its one primary user question.
- Use a three-layer hierarchy: hero state/value, supporting choices or metrics, tertiary detail/disclosure.
- Place persistent labels above or inside the control boundary; use one reading edge for multi-line content.
- Pair state with words, not colour alone: for example, a dot plus “Ready on your avatar.”

### Spacing and surfaces

- Use proximity and consistent vertical rhythm to form default groups.
- Use a surface when it expresses selection, interaction, elevation, warning, or meaningful emphasis.
- Prefer selective separators over boxed sections and full grids.
- Keep interactive targets comfortably large even when the visual treatment is compact.

### Colour and modes

- Neutral canvas and content surfaces carry most of the interface.
- Accent colour marks the active navigation item or primary action.
- Success, warning, and error colours always retain their semantic jobs.
- A functional region uses one coherent light/dark contrast model.
- Decorative gradients remain behind low-density focal content and degrade gracefully.

### Forms

- Use real `<form>` submission and persistent `<label>` relationships.
- Ask only for information the current step needs.
- Make default or estimated values explicit; never classify fallback data as measured without an intentional choice.
- Use `inputMode`, input type, min/max, live formatting, and clear unit suffixes to reduce errors.
- Validate close to the field, preserve user input on errors, and keep the next action in a stable location.
- Use progressive disclosure for help and advanced detail, not for required meaning.

### Motion

- Animate changes of state or spatial relationship, not every mounted element.
- Reuse a small set of entrance, selection, disclosure, and completion curves/springs.
- Keep feedback fast enough that it does not delay the task.
- Respect `prefers-reduced-motion`; reduced motion still needs immediate state feedback.

### Components and code

- Reuse semantic tokens and app-only primitives before adding new visual constants.
- Model variants with independent properties such as `variant`, `tone`, `size`, and `state`.
- Use the same state names in UI copy, component props, and domain logic where possible.
- Empty, loading, processing, success, unsupported, and failure states are first-class component states.

## Mirra implementation boundaries

The route boundary in `website/frontend/src/router.tsx` defines the protected/product surfaces targeted by this work:

- `/measurements`
- authenticated onboarding flows
- `/studio`
- `/profile/*`

The following are intentionally untouched by this implementation:

- `/`, `/pricing`, `/faq`, `/join`, `/terms`, `/privacy`, and `/security`;
- all files under `features/marketing/**`;
- pre-login auth screens;
- global visual defaults that could leak into the marketing site.

App changes should stay page-local or under app-only feature folders. Shared global styles and primitives must not be restyled in a way that alters marketing output.

## Completed application changes

### Measurement intake

- Converted the interaction into a real accessible form with persistent labels and semantic fieldsets.
- Required explicit avatar-model and measurement-accuracy choices instead of silently labelling fallback values accurate.
- Added numeric keyboard hints, min/max rules, live range feedback, clamping, unit conversion, and first-error focus.
- Added a compact completion/validity summary and one stable **Save and continue** action.
- Grouped the task with whitespace and selective surfaces rather than additional dividers.

### Studio

- Established persistent, readable app navigation and a stronger selected-piece/status hierarchy.
- Kept one **Add to preview cart** action instead of repeating it in the product panel and Hanger.
- Replaced implementation-state labels with human-readable try-on status, explanatory text, and a non-colour cue.
- Made unavailable checkout and commerce pricing explicit while preserving the cart.
- Added visible retry for session startup, account-scoped Studio state, and guarded missing size, image, render, and catalogue data.
- Added reusable, honest thumbnail and mannequin placeholders so incomplete live data never becomes a broken image or fictitious product visual.

### Profile

- Replaced blank loading returns with spatially stable skeleton/status states.
- Strengthened navigation between Studio, Fit Profile, Avatar, Saved Looks, and Privacy.
- Added app-scoped focus treatment, responsive header behavior, reduced-motion/transparency handling, and clearer control labels.
- Used honest empty states when an avatar, saved-look image, or render preview is unavailable; unavailable controls are hidden rather than shown as dead affordances.
- Added dirty-state save behavior, optimistic consent feedback with rollback, and visible save/delete/sign-out failures.
- Replaced unverified privacy and session claims with product-accurate, explicitly review-pending language.

## Acceptance criteria

- No public marketing file or route is changed by this implementation.
- A keyboard user can reach, understand, and operate every changed control.
- Visible labels persist before, during, and after data entry.
- Status is never communicated by colour alone.
- Reduced-motion users receive equivalent immediate feedback.
- Unsupported or unavailable features do not claim success or destroy user state.
- TypeScript, lint, and whitespace checks pass for the edited application code.
- Visual QA covers mobile and desktop authenticated layouts without using production user data.

## Verification performed

- `npm run typecheck`: passed.
- `npm run lint`: passed with no warnings or errors.
- `npm run build`: passed; Vite completed a production build.
- `git diff --check`: passed.
- A scoped Prettier check covering every implementation file and this document: passed.
- Desktop visual QA used the normal 1280 × 720 application viewport; responsive QA used a temporary 390 × 844 viewport.
- Authenticated routes were rendered against a disposable local response stub, so the verification did not read or write a production account or database.
- Visual/semantic checks covered `/measurements`, `/studio`, `/profile`, `/profile/avatar`, `/profile/measurements`, `/profile/signature-looks`, and `/profile/privacy`.
- Interaction checks covered first-error focus, live measurement range errors, fit-profile dirty state, consent rollback, Studio cart retention, missing-price treatment, and disabled checkout.
- A fresh Studio load produced no browser console warnings or errors after the missing-image fallbacks were added.

The repository-wide format command still reports 11 unrelated, pre-existing files outside this implementation's edit set. They were deliberately left alone, particularly the public marketing files, to honor the post-login-only boundary.

## Known product-data limits

The current live API mapper does not yet supply avatar preview imagery, garment thumbnails/render assets, or real commerce prices. The upgraded UI does not disguise those integration gaps: it shows deliberate placeholders, “preview unavailable,” and “price unavailable,” and keeps checkout disabled. Connecting those assets and prices is backend/catalogue work rather than a visual-design change.

The unguarded `/onboarding/qr` route was also excluded from this implementation. Treating it as post-login-only requires an explicit route or page guard before it can safely inherit authenticated-app assumptions.
