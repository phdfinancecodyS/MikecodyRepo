# CODY START HERE - Ask Anyway Status Update (April 2026)

> This file is the first thing to read when you open this repo.
> Last updated: 2026-04-03 by Mike

---

## Plain-language status (April 3, 2026)

Here's where we're at in normal human terms.

The backend conversation engine (the thing that runs the quiz, scores it, matches you to a guide, and routes you to the right offer) is done and tested. We threw 100 automated tests at it across 5 difficulty levels, including adversarial garbage input, concurrent sessions, crisis safety checks, and full end-to-end pipelines. It passes all of them.

The frontend quiz is no longer a developer prototype. It's a real step-by-step wizard now. One question per screen, progress bar at the top, back button, auto-advances when you pick an answer, and saves your progress so you don't lose it if you accidentally close the tab. After the 10 scored questions, it walks you through the topic matcher (3 questions), audience picker (17 options), and an optional contact capture screen, then submits everything and shows your results.

The results page respects the safety rules we locked in: if you score critical, you see crisis resources immediately and nothing else above them. No sales pitch above the fold for someone in crisis. High risk shows crisis resources before any offers. Low and moderate risk see their matched guide and offer options first, with crisis resources at the bottom. Those rules are enforced in the code, not just in a spec doc.

The landing page is built. Hero section, how-it-works breakdown, a testimonial placeholder, and two calls to action that link to the quiz. Crisis resources in the footer. LCSW credential mentioned.

On the backend infrastructure side: sessions now persist to disk, so if the server restarts you don't lose active quiz sessions. The Stripe webhook handler is fully wired to trigger email delivery through SendGrid and SMS enrollment through Twilio when someone purchases. The analytics endpoint stores events to the database. Facebook Pixel and Google Analytics load from environment variables (so they're off in dev, on in production). Sentry error monitoring is installed with a global error boundary that still shows crisis resources even if the app crashes.

All 4,036 content files that had em dashes got cleaned up (your preference, no em dashes anywhere). The two legacy snapshot directories that were eating 96MB of space are gone. The old Next.js version that had 4 known CVEs got upgraded to 15.5.14 with zero vulnerabilities.

What's left is external provisioning: you need a Supabase project with the migrations applied, Stripe products created with real price IDs, SendGrid and Twilio accounts configured, and analytics/monitoring accounts set up. All the env vars are templated in `web/.env.local` and there's a script (`scripts/check-infra.sh`) that validates everything is connected.

Short version: the code is done. What's left is accounts, keys, and deployment.

---

## What changed since the March 20 handoff

Everything below was built and tested. The backend passes 100/100 beta tests across 5 progressive stress levels. The Next.js frontend builds clean with 0 npm vulnerabilities.

### Done (17 items completed)

| # | What | Where |
|---|------|-------|
| 1 | **POLICY_RE regex fixed** - word-stem matching now catches all forms (diagnose, diagnosed, diagnosing, etc.) | `ask-anyway/cce-backend/src/engine.py` |
| 2 | **Next.js upgraded to 15.5.14 + React 19** - 0 CVEs, 0 npm audit vulnerabilities | `web/package.json` |
| 3 | **Duplicate return bug fixed** in therapist endpoint | `ask-anyway/cce-backend/src/app.py` |
| 4 | **Environment template created** with all 18 env vars documented | `web/.env.local` |
| 5 | **Kit zips built** - 1,343 zips (guide + 2 worksheets each) across all 17 audiences | `output/kits/` |
| 6 | **Multi-step quiz wizard** - one question per screen, progress bar, back button, auto-advance, sessionStorage persistence | `web/app/quiz/page.tsx` |
| 7 | **Risk-band results pages** - Critical: crisis first, no paid offers. High: crisis before offers. Low/Moderate: offers then crisis | Built into quiz wizard |
| 8 | **Landing page** - hero, how-it-works, social proof, dual CTAs, crisis footer, LCSW credential | `web/app/page.tsx` |
| 9 | **Persistent CCE sessions** - file-backed with in-memory cache, survives server restart | `engine.py` (_save_session/_load_session) |
| 10 | **Email/SMS fulfillment** - SendGrid transactional email + Twilio SMS enrollment wired into Stripe webhook | `web/api/webhooks/stripe/route.ts` |
| 11 | **FB Pixel + GA4** - loads conditionally from env vars, includes trackEvent() helper | `web/app/analytics.tsx` |
| 12 | **Sentry error monitoring** - @sentry/nextjs installed, client/server/edge configs, global error boundary | `web/sentry.*.config.ts`, `web/app/global-error.tsx` |
| 13 | **Infrastructure checker script** - validates all env vars, checks for Supabase/Stripe CLI | `scripts/check-infra.sh` |
| 14 | **Em dash audit** - stripped from all 4,036 content files (0 remaining) | `scripts/strip_em_dashes.py` |
| 15 | **Q8 scoring divergence documented** - CCE backend [0,2,3,4] vs frontend [0,1,2,3] | engine.py docstring |
| 16 | **Legacy stubs deleted** - removed 96MB of duplicate snapshot directories | |
| 17 | **Full validation** - Next.js build clean, beta tests 100/100, npm audit 0 vulns | |

---

## What YOU still need to provision (can't be done in code)

These are the external accounts/keys that go into `web/.env.local`:

| Service | What to do | Env var(s) |
|---------|-----------|------------|
| **Supabase** | Create project, run 2 migrations from `supabase/migrations/` in order | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` |
| **Stripe** | Create products: Guide ($9), Kit ($19), SMS ($4.99/mo recurring), Bundle ($34). Get price IDs | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_IDS` |
| **SendGrid** | Create account, verify sender, create delivery templates (guide + kit) | `SENDGRID_API_KEY`, template IDs |
| **Twilio** | Get account + phone number for Check On Me SMS | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` |
| **Google Analytics** | Create GA4 property, get measurement ID | `NEXT_PUBLIC_GA4_MEASUREMENT_ID` |
| **Facebook** | Create pixel in Events Manager | `NEXT_PUBLIC_FB_PIXEL_ID` |
| **Sentry** | Create project at sentry.io | `NEXT_PUBLIC_SENTRY_DSN`, `SENTRY_AUTH_TOKEN` |

Run `bash scripts/check-infra.sh` after filling in values to verify everything connects.

---

## How to run locally

**CCE Backend (FastAPI):**
```bash
cd ask-anyway/cce-backend
source .venv/bin/activate
PYTHONPATH="$PWD" python -m uvicorn src.app:app --host 0.0.0.0 --port 8000
```

**Next.js Frontend:**
```bash
cd web
npm install
npm run dev
```

**Run beta tests (backend must be running on :8000):**
```bash
cd ask-anyway
python3 beta_test_progressive.py
```
Expected: 100/100 across 5 levels.

---

## Reading order (unchanged from March handoff)

1. **This file** (you're here)
2. `planning/CODY-VSCODE-IMPORT-RUNBOOK.md` - original orientation
3. `planning/TECH-HANDOFF-FOR-CODY.md` - full implementation spec (phases A-F)
4. `planning/QUIZ-IMPLEMENTATION-CONTRACT.md` - scoring/routing/CTA rules
5. `web/api/README.md` - API scaffold docs
6. `planning/API-ROUTE-SPECS.md` - request/response contracts
7. `planning/BACKEND-SYSTEM-CONTRACT.md` - database entity definitions

---

## File counts

- 4,117 content markdown files (79 base guides x 17 audiences + worksheets + modules + lead magnet)
- 1,343 kit zips (gitignored build artifacts: run `python3 scripts/build_kit_zips.py` to regenerate)
- 7 API routes (all implemented, not stubs)
- 100/100 beta tests passing
- 0 npm vulnerabilities
- 0 em dashes in content
