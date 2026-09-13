# 05 — Security gaps before launch

Status: *discussion phase — documented only, nothing fixed, no files/code changed*
Written: *2026-09-12*
Source: `.agent/saumy/02-remaining-build-list.md` Security/launch-readiness
section (S1-S8), each one re-checked directly against the current backend
code before writing this file — noted per item whether it was freshly
confirmed or carried forward from the build list unverified.

---

## S1 — API docs (`/docs`, `/redoc`, `/openapi.json`) are wide open

**Confirmed directly** — `website/backend/src/main.py:40`:
`FastAPI(title=..., version=..., lifespan=lifespan)`, no `docs_url`,
`redoc_url`, or `openapi_url` arguments, no environment check anywhere in
the file.

**Why it matters:** all three are live, unauthenticated, and fully
interactive in every environment — dev or production, no distinction.
Anyone who finds the URL gets a complete, clickable map of every route and
every request/response schema, and can fire live requests at the API
straight from the browser. Cheapest fix on this whole list — just needs an
environment check.

## S2 — No rate limiting anywhere

**Confirmed directly** — grepped the whole backend for
`slowapi`/`rate_limit`/`Limiter`: zero matches.

**Why it matters, and why it's worse here than for a typical web app:**
applies to auth endpoints (unlimited request volume) *and* to avatar/VTO
generation, where each request holds the one CLO worker exclusively for
~90 seconds. Since there's no per-user or per-IP limit, a handful of rapid
repeat requests from one person — malicious or just an impatient
double-click — can monopolize the only worker and make the site
unresponsive for every other user queued behind it. The single-CLO-worker
bottleneck makes this a real denial-of-service risk, not a theoretical one.

## S3 — No brute-force protection on login

Not independently re-verified beyond the build list, but consistent with
S2's finding (no rate-limiting infrastructure exists at all). No
login-specific lockout/backoff (e.g. "N failed attempts, wait 60s").
Without it, credential-stuffing or password-guessing against real user
accounts is unthrottled.

## S4 — Production `ACCESS_TOKEN_SECRET` — partially closed

**Confirmed directly** — `website/backend/src/config.py:45`:
`access_token_secret: str = Field(min_length=32)`, no default value. The
app now fails to start if this isn't set to something real, closing the
"silently ran with a weak/missing default" failure mode.

**What's left:** purely operational — actually provisioning and setting a
real, sufficiently random secret in whatever hosting environment is used
for launch (Render, etc.). The code-side guard is done; the
deployment-side step is not.

## S5 — `COOKIE_SECURE`/`CORS_ORIGINS` locked to the real domain — configured but unverified

**Confirmed directly (code side)** — both are already environment-driven:
`cookie_secure` setting drives `secure=` on every `set_cookie` call in
`auth/controller.py`; `cors_origin_list` drives `allow_origins` in
`main.py:44`.

**Why it matters:** the gap isn't the code, it's that nobody has actually
deployed and checked these are set correctly for the real production
domain. A misconfigured `CORS_ORIGINS` either blocks the real frontend
from reaching the API, or — worse — accepts requests from anywhere.

## S6 — Refresh-cookie behavior across the Vercel↔Render domain boundary — untested

**Confirmed directly, and a concrete risk identified** —
`website/backend/src/auth/controller.py`: every cookie (`_set_refresh_cookie`,
the Google OAuth state/next cookies) is set with `samesite="lax"`,
hardcoded, not configurable.

**Why it matters:** if the frontend (e.g. Vercel) and backend (e.g. Render)
end up on different domains, those are different *sites* to the browser.
`SameSite=Lax` cookies are sent on top-level navigation (typing a URL,
clicking a link) but are **not reliably sent on cross-site `fetch`/`XHR`
calls** — which is exactly how a single-page app's frontend talks to its
API. If that's the real deployment shape, the refresh cookie may simply
never reach the backend on a normal API call, silently breaking session
refresh in production while working perfectly in local dev (where
frontend and backend often share `localhost` and count as the same site).
This is the item most likely to cause a "works locally, breaks in
production" surprise, and is worth deciding on *before* launch rather than
discovering it after.

## S7 — No CSP or security headers on the frontend

Not independently re-verified beyond the build list. No
Content-Security-Policy, `X-Frame-Options`, `X-Content-Type-Options`, etc.

**Why it matters:** these limit the damage if any other frontend bug (e.g.
somewhere user-supplied content gets rendered without proper escaping)
turns into a real cross-site-scripting exploit — a safety net for a class
of bug that can't be fully ruled out by code review alone.

## S8 — No monitoring/logging for auth failures or API errors

**Partially checked** — `main.py` calls `register_exception_handlers(app)`
generically; no structured logging of failed logins, repeated 401/403s, or
unusual error rates was found beyond that.

**Why it matters:** without this, if any of S1-S7 actually gets probed or
exploited after launch, there's currently no way to notice from the
system itself — it would surface only through user complaints, after the
fact.

---

## Priority read (discussion only, not yet agreed as a plan)

Given the specific constraint of one CLO worker as the entire compute
bottleneck:

1. **S2** (rate limiting) is more urgent here than for a generic web app —
   the compute-exhaustion angle (one request = ~90s of exclusive CLO time)
   makes this a real availability risk, not just an abuse-prevention
   nice-to-have.
2. **S1** (docs gating) is the cheapest fix on the list and should just be
   done regardless of sequencing.
3. **S6** (refresh-cookie cross-domain behavior) is the one most likely to
   silently break something the moment the site is actually deployed to
   two different domains — worth resolving before launch, not discovering
   after.

Nothing above has been fixed. This file documents the discussion only.
