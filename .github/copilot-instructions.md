# Ask Anyway — Copilot Workspace Instructions

## What This Project Is

Ask Anyway is a mental health digital product that teaches everyday people how to start, stay in, and follow through on a conversation about suicide. It is built on clinical expertise (LCSW) and personal loss experience.

**Business model:** TikTok organic → free quiz funnel → digital product offers + SMS subscription.

**Products:** Guide ($9), Kit ($19), Check On Me SMS ($4.99/mo), Bundle ($34).

---

## Architecture Overview

**Stack:** Next.js App Router + Supabase + Stripe + Twilio (SMS) + SendGrid/ConvertKit (email)

**User flow:**
1. TikTok video (with UTM link) → quiz landing page
2. 10-question scored quiz (0–30 points, 4 risk bands)
3. Risk-band results page (crisis resources always visible)
4. Topic matcher (3 questions → matched guide) — skipped for critical
5. Audience matcher (identity/context → 1 of 17 audience buckets) — skipped for critical
6. Recommendation stack (guide + offer lane + crisis resources)
7. Optional email/SMS capture (never before crisis actions on critical)
8. Stripe checkout → webhook → fulfillment (email delivery, SMS enrollment)
9. Post-quiz email sequence (risk-personalized) + Check On Me SMS (weekly)

---

## Scoring Rules (Non-Negotiable)

- 10 questions, each scored 0–3, total range 0–30
- 0–10 = low_risk, 11–20 = moderate_risk, 21–25 = high_risk, 26–30 = critical
- Q5 = 3 → force critical (override)
- Q5 = 2 → minimum high_risk (override)
- Critical results: crisis resources FIRST, no paid products above crisis CTAs, contact capture CANNOT appear before crisis actions

---

## Content System

**Total content files: 4,116 markdown files**

- 79 base topic guides in `content/topic-guides/` (33 chapters + 28 splits + 18 new-topics)
- 1,343 audience-specific guide variants in `content/topic-guides/audience-slants/` (79 × 17 audiences)
- 2,686 standalone worksheets in `content/worksheets/` (2 per guide × 79 × 17)
- 3 program modules in `content/modules/`
- 1 lead magnet in `content/lead-magnet/`

**17 audience buckets:** addiction-recovery, bipoc-racial-trauma, christian, chronic-illness-chronic-pain, educators, faith-beyond-christian, first-responder, general-mental-health, grief-loss, healthcare-workers, high-stress-jobs, lgbtq, military-veteran, neurodivergent, single-parent, social-workers-counselors, young-adult-gen-z

**Voice standard:** Warm, direct, second-person, contractions, humor, "session-5 energy." Never clinical or academic. Every file includes an educational disclaimer and 988/Crisis Text Line resources.

---

## Source-of-Truth Files (These Win When Docs Conflict)

| Domain | File |
|--------|------|
| API contracts | `planning/API-ROUTE-SPECS.md` + `quiz/api-contracts.json` |
| Database schema | `planning/BACKEND-SYSTEM-CONTRACT.md` + `supabase/migrations/` |
| Scoring & routing rules | `planning/QUIZ-IMPLEMENTATION-CONTRACT.md` |
| Product routing | `quiz/recommendation-routing-config.json` |
| Guide catalog | `quiz/base-guide-catalog.json` + `planning/GUIDE-OFFER-MAPPING.csv` |
| Audience resolution | `quiz/audience-bucket-flow.json` + `planning/AUDIENCE-SLANT-MANIFEST.csv` |
| Fulfillment | `quiz/fulfillment-config.json` |
| Implementation scaffolds | `web/api/` |

---

## API Surface (7 Endpoints — Do Not Collapse Into One)

- `POST /api/quiz/score` — Score answers, assign risk band, persist session
- `POST /api/quiz/topic-match` — Match topic from post-quiz answers
- `POST /api/quiz/audience-match` — Match audience bucket(s)
- `POST /api/quiz/recommendation` — Resolve final guide + offer stack
- `POST /api/checkout/session` — Create Stripe checkout session
- `POST /api/webhooks/stripe` — Handle purchase → trigger fulfillment
- `POST /api/analytics/event` — Track quiz/CTA/conversion events

Handlers are scaffolded at `web/api/` as Next.js App Router route.ts files. Copy into `app/api/` of the target Next.js project.

---

## Database (Supabase)

Migrations in `supabase/migrations/` — apply in filename order:
1. `20260320153000_backend_architecture.sql` — core tables
2. `20260320160000_rls_policies.sql` — RLS policies

Core tables: `leads`, `quiz_sessions`, `topic_match_sessions`, `audience_match_sessions`, `guide_recommendations`, `product_clicks`, `purchases`, `fulfillment_events`

Do NOT recreate legacy `users` or `quiz_responses` tables. Use the migration as written.

---

## Known TODOs (Stubs Requiring Implementation)

1. `web/api/quiz/topic-match/route.ts` — replace stub matchDomain() with config-driven matching using `quiz/topic-matcher-flow.json`
2. `web/api/quiz/recommendation/route.ts` — resolve human-readable title from `quiz/base-guide-catalog.json`
3. `web/api/webhooks/stripe/route.ts` — wire email delivery (SendGrid/ConvertKit) + SMS enrollment (Twilio)
4. `web/api/analytics/event/route.ts` — persist non-CTA events to analytics store
5. Frontend quiz UI — wire pages to call endpoints in sequence, handle critical fast-path safely

---

## Environment Variables Required

```
SUPABASE_URL
SUPABASE_SERVICE_KEY
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
STRIPE_PRICE_IDS (JSON map by product id)
```

Required packages: `@supabase/supabase-js`, `stripe`

---

## Key Orientation Files (Read in This Order)

1. `planning/CODY-VSCODE-IMPORT-RUNBOOK.md` — single-page orientation
2. `planning/TECH-HANDOFF-FOR-CODY.md` — full implementation spec with phases A–F
3. `planning/QUIZ-IMPLEMENTATION-CONTRACT.md` — scoring/routing/CTA rules
4. `web/api/README.md` — API scaffold docs + known TODOs
5. `planning/API-ROUTE-SPECS.md` — full request/response contracts
6. `planning/BACKEND-SYSTEM-CONTRACT.md` — database entity definitions

---

## Safe Messaging Rules

All content follows AFSP, SAMHSA, JED Foundation, and 988 standards. Never sensationalize or include method details. Crisis resources (988, Crisis Text Line) must be present on every result page and in every content file. Content is educational — not therapy, not diagnosis.

---

## Quality Assurance

Run `python3 scripts/full_workspace_audit.py` to validate:
- File counts and completeness
- Voice consistency sampling
- Quiz reference resolution
- Audience coverage
- Scoring and safety logic
- Product alignment
- Manifest sync
- Placeholder/secret scanning

Expected result: 0 CRITICAL, 0 WARNING.
