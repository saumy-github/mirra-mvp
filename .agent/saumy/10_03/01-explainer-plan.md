# 01 — Plan: explaining this repo to a true beginner, one part at a time

*Status: proposed — confirm or edit before we start part 2*
*Compiled: 2026-10-03*

## How this will work

- One part per message. I explain only that part — short, plain language, no code dumps unless the part is specifically about reading code.
- I wait for you to say "next", ask a question, or say "go deeper" before moving on. I will not jump ahead or summarize future parts early.
- Each part builds only on parts already covered. If a part needs something from later, I'll name it ("we'll get to *how* in Part 14") instead of explaining it early.
- Parts are small on purpose. Some will be two sentences. That's fine — the goal is nothing ever lands in one go.
- You can reorder: if you already know a part, say "skip" and we move on.
- This file is the table of contents only. It does not explain anything itself — if reading this plan already feels like too much, tell me and I'll shrink it to headline-only.

47 parts, in 8 phases. Phase order = the order a new teammate would actually need the pieces, not the order the code was written in.

---

## Phase A — Orientation (no code, no folders yet)

1. What Mirra is, in one paragraph, zero jargon
2. The problem it's solving, in a story (why online clothes shopping fails today)
3. The 3-step mental model: body twin → garment pattern → try-on — as a story, not as code
4. The two layers you'll keep separating: "the pipeline" (CLO3D scripts) vs "the website" (what a shopper actually opens in a browser)
5. The cast of tools, named only, one sentence each: CLO3D, Python, MongoDB, FastAPI, React, Docker, Redis — what each one *is*, not how Mirra uses it yet

## Phase B — Finding your way around the repo (structure only, still no deep code)

6. What "repo root" means and how to always know where you are
7. The top-level folders, named and one-line each — no contents yet
8. Which folders are "pipeline" and which are "website" — sorting Phase B's list into the Phase A mental model
9. `.claude/` and `.agent/` — what these are for and why they're not application code
10. How to tell a *stale* doc from a *current* one in this repo (and why that happens with multiple people + AI tools writing docs)

## Phase C — Step 1: Avatar generation (pipeline only)

11. What a "digital twin avatar" actually is here — not a drawing, a measured 3D mesh
12. What goes in (your measurements) and what comes out (a `.avt` file) — black box view only
13. The one command that runs it, and what "running a pipeline step" means in practice
14. Opening `clo_avatar_generation/` — what the folder contains, at a glance
15. The 11-step pipeline, walked step by step, in plain language (this part will likely split into 2-3 sub-conversations once we're there)
16. Where the output lands and what each output file is for
17. What "70% complete" means for this step — what still breaks and why

## Phase D — Step 2: Product ingestion (pipeline only)

18. What this step is actually converting (a product photo) into (a sewing-pattern-like shape)
19. The 5-stage extraction, named one at a time
20. What a DXF file is and why patterns are exported that way
21. The "half-girth" convention — what it means and why it's the one rule that breaks everything downstream if violated
22. Where this step currently gets stuck (the output-folder mismatch) — just the shape of the problem, not the fix

## Phase E — Step 3: Virtual try-on (pipeline only)

23. What "physics simulation" means here, in plain terms (cloth draping on a body, not a game engine)
24. How Step 3 takes Step 1's avatar + Step 2's pattern and combines them
25. What a "seam" is in this system and why T-shirts need 10 of them
26. Reading a `native_vto_report.json` — what success and failure look like in that file

## Phase F — CLO3D itself (the one piece that isn't ordinary code)

27. What CLO3D is as a standalone piece of software, before Mirra touches it
28. What a "plugin" means here and why Mirra needed to build one
29. The REST API idea — how Python code "talks to" an app running on your desktop
30. Why only one job can run in CLO at a time (and what breaks if you ignore that)

## Phase G — The website (this is where most of the recent work lives)

31. What the website adds on top of the pipeline — the shopper's point of view, one click at a time
32. Backend vs frontend, explained with the actual two folders (`website/backend`, `website/frontend`)
33. What FastAPI is doing in `website/backend` — a request's journey in plain words
34. What MongoDB is storing and why a database instead of files
35. Reading a backend "module" folder (using one real one, e.g. `auth/`) — what each file inside is for
36. The worker — what a "background job queue" is and why avatar/try-on generation can't just happen instantly on request
37. Walking through the other backend modules, one at a time, each its own short part (users, measurements, avatars, catalog, tryon, signature looks, analytics, join)
38. What React is doing in `website/frontend` — a page's journey in plain words
39. How routes map to pages — using the real route table, one group at a time (marketing, auth, profile, studio, dashboard)
40. The merchant dashboard — what it is today (a working prototype) vs what it will be

## Phase H — Where things actually stand today

41. What works end-to-end right now, if you tried it yourself today
42. What's built but blocked, and why
43. What hasn't been started yet
44. The open issues that matter most — security, architecture, performance — one group at a time
45. How to read `.agent/saumy/02-remaining-build-list.md` yourself, so you don't need me to re-explain it every time
46. How to read `markdown-inventory.md` yourself — what "current / mixed / outdated" mean and why that file exists
47. How to pick this back up next time, alone — the habit, not just the docs

---

## Notes on sequencing

- Phases C/D/E (the pipeline) come before Phase G (the website) on purpose — the website is a thin layer that *calls* the pipeline, so the pipeline needs to make sense first.
- Phase F (CLO3D) sits between the pipeline and the website because it's the one dependency both layers lean on, and it behaves unlike normal code (a desktop app with a queue, not a library).
- Phase H is last on purpose — "what's broken" only makes sense once you know what the thing is supposed to do.
- Some numbered parts (15, 37, 39, 44) are naturally multi-message; I'll say so when we get there and split further rather than compress.

Tell me if any phase should move earlier/later, if you want a phase dropped (e.g. you already know what MongoDB/React are), or if 47 parts is still too coarse somewhere and should be split further.
