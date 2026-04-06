# Ask Anyway: Developer README

**Product:** Ask Anyway: a practical skills-based program teaching everyday people how to start, stay in, and follow through on a conversation about suicide.

**Primary channel:** TikTok organic → free quiz funnel → digital product offers + SMS subscription

**Built by:** Licensed Clinical Social Worker (content/clinical) + Cody Sullivan (tech/business)

**Last updated:** 2026-04-03

---

## Quick Start for Cody

> **Start here.** Read `CODY-START-HERE.md` at the repo root first. It has a plain-language status update and a full changelog of everything built since the March 20 handoff.

Then open these files in order. If anything conflicts with an older doc, these win.

| Order | File | What it tells you |
|-------|------|-------------------|
| 0 | `CODY-START-HERE.md` | April 2026 status update, changelog, provisioning checklist, local run instructions |
| 1 | `planning/CODY-VSCODE-IMPORT-RUNBOOK.md` | Single-page orientation: what's built, what to open, env vars, VS Code workflow |
| 2 | `planning/TECH-HANDOFF-FOR-CODY.md` | Full tech handoff: phases A–F, scoring logic, Stripe, email/SMS, deployment checklist |
| 3 | `planning/QUIZ-IMPLEMENTATION-CONTRACT.md` | Non-negotiable product rules, scoring bands, routing contract, result CTAs, QA gate |
| 4 | `web/api/README.md` | API scaffold docs: file structure, env vars, npm packages, known TODOs |
| 5 | `planning/API-ROUTE-SPECS.md` | Full request/response contracts for all 7 endpoints |
| 6 | `planning/BACKEND-SYSTEM-CONTRACT.md` | Database entity definitions, persistence fields, source-of-truth file list |
| 7 | `quiz/api-contracts.json` | Machine-readable API contracts (mirrors the markdown spec) |

---

## One-Place Local Commands (This TikTok Folder)

Run everything from this workspace root:

```bash
./install-cody-command.sh
cody
```

Global command setup:
- Run `./install-cody-command.sh` once to add `cody` to PATH.
- After that, use `cody` from terminal.
- `cody` auto-pulls latest from origin when the working tree is clean.

Direct command from repo root:

```bash
./cody
```

One-word command details:
- Rehydrates backend Python environment
- Installs frontend dependencies
- Starts backend and frontend
- Validates health endpoints
- Opens canonical UI automatically

If you want no browser launch:

```bash
./cody --no-open
```

Manual launcher:

```bash
./run-ask-anyway-shared.sh
```

Smoke test the backend from this same folder:

```bash
./smoke-test-ask-anyway.sh
```

Stop local services (frontend/backend/demo ports):

```bash
./stop-ask-anyway-shared.sh
```

Open both local pages in your browser:

```bash
./open-ask-anyway.sh
```

Pull latest changes from GitHub into the shared Ask Anyway repo:

```bash
./pull-ask-anyway.sh
```

Export your local changes back to GitHub with one command:

```bash
./export-ask-anyway.sh "your commit message"
```

---

## What's in This Workspace

### Content System: 4,116 markdown files, fully written

| Layer | Count | Location |
|-------|-------|----------|
| Base topic guides | 79 | `content/topic-guides/chapters/` (33), `splits/` (28), `new-topics/` (18) |
| Audience-specific variants | 1,343 | `content/topic-guides/audience-slants/{audience}/` (79 guides × 17 audiences) |
| Standalone worksheets | 2,686 | `content/worksheets/{audience}/` (2 per guide × 79 × 17) |
| Program modules | 3 | `content/modules/module-{1,2,3}-*.md` |
| Lead magnet | 1 | `content/lead-magnet/ask-anyway-content.md` |
| Frontline Folks reference | 157 | `content/frontline-folks-guides/mikenfs/` |

**17 audience buckets:**
`addiction-recovery` · `bipoc-racial-trauma` · `christian` · `chronic-illness-chronic-pain` · `educators` · `faith-beyond-christian` · `first-responder` · `general-mental-health` · `grief-loss` · `healthcare-workers` · `high-stress-jobs` · `lgbtq` · `military-veteran` · `neurodivergent` · `single-parent` · `social-workers-counselors` · `young-adult-gen-z`

**Voice standard:** Warm, direct, second-person, uses contractions and humor, "session-5 energy", as if talking with the reader, not at them. Every file has an educational disclaimer and 988/Crisis Text Line resources.

---

### Quiz & Recommendation Engine: 10 JSON config files

| File | Purpose |
|------|---------|
| `quiz/quiz-content.json` | 10 scored questions (0-3 each, 0-30 total) |
| `quiz/topic-catalog.json` | 47 frontline topics mapped to domains |
| `quiz/topic-matcher-flow.json` | 3-question post-quiz topic matcher with 14 topicHints |
| `quiz/audience-bucket-flow.json` | Audience identity/context matcher (17 buckets) |
| `quiz/base-guide-catalog.json` | 79 base guides with domains, tags, offer lanes |
| `quiz/recommendation-routing-config.json` | Risk-based routing pipeline (what to show/hide per band) |
| `quiz/product-catalog.json` | 4 products: Guide ($9), Kit ($19), SMS ($4.99/mo), Bundle ($34) |
| `quiz/fulfillment-config.json` | Post-purchase delivery rules by product |
| `quiz/conversation-branch-flow.json` | Post-quiz conversational branching |
| `quiz/api-contracts.json` | Machine-readable API request/response contracts |

**Scoring:**
- 0–10 = `low_risk` · 11–20 = `moderate_risk` · 21–25 = `high_risk` · 26–30 = `critical`
- Q5 = 3 → force `critical` · Q5 = 2 → minimum `high_risk`
- Critical results: crisis resources first, no paid products above crisis CTAs, contact capture blocked before crisis actions

---

### Backend: Supabase + Next.js App Router + Stripe

**Database (Supabase):**

| File | What it creates |
|------|-----------------|
| `supabase/migrations/20260320153000_backend_architecture.sql` | Core tables: `leads`, `quiz_sessions`, `topic_match_sessions`, `audience_match_sessions`, `guide_recommendations`, `product_clicks`, `purchases`, `fulfillment_events` |
| `supabase/migrations/20260320160000_rls_policies.sql` | Row Level Security policies (service-role server access pattern) |
| `supabase/migrations/20260402120000_analytics_events.sql` | Dedicated `analytics_events` table for non-CTA event persistence |

**API Routes (scaffolded, Next.js App Router):**

| Route | Handler | Purpose |
|-------|---------|---------|
| `POST /api/quiz/score` | `web/api/quiz/score/route.ts` | Score answers, assign risk band, persist session |
| `POST /api/quiz/topic-match` | `web/api/quiz/topic-match/route.ts` | Match topic from post-quiz questions |
| `POST /api/quiz/audience-match` | `web/api/quiz/audience-match/route.ts` | Match audience bucket(s) |
| `POST /api/quiz/recommendation` | `web/api/quiz/recommendation/route.ts` | Resolve final guide + offer stack |
| `POST /api/checkout/session` | `web/api/checkout/session/route.ts` | Create Stripe checkout session |
| `POST /api/webhooks/stripe` | `web/api/webhooks/stripe/route.ts` | Handle purchase → trigger fulfillment |
| `POST /api/analytics/event` | `web/api/analytics/event/route.ts` | Track quiz/CTA/conversion events |

**Shared libraries:** `web/api/_lib/types.ts` (TypeScript types), `supabase.ts` (client factory), `scorer.ts` (scoring + validation)

**Current backend status:**
1. `topic-match/route.ts`: implemented with config-driven matching against `quiz/topic-matcher-flow.json`
2. `recommendation/route.ts`: resolves guide title and offer lane from `quiz/base-guide-catalog.json`
3. `webhooks/stripe/route.ts`: provider dispatch code added for SendGrid and Twilio; live credentials still required for runtime verification
4. `analytics/event/route.ts`: non-CTA events now persist to `analytics_events`
5. Frontend: root `web/` folder now contains a runnable Next.js app shell, API route wrappers, and a first quiz page at `web/app/quiz/page.tsx`

---

### Planning & Strategy — 24 docs

| Category | Key files |
|----------|-----------|
| Architecture | `PLATFORM-ARCHITECTURE-BLUEPRINT.md`, `BACKEND-SYSTEM-CONTRACT.md` |
| API contracts | `API-ROUTE-SPECS.md`, `QUIZ-IMPLEMENTATION-CONTRACT.md` |
| Content pipeline | `GUIDE-BUILD-MANIFEST.csv` (79 rows), `GUIDE-OFFER-MAPPING.csv`, `AUDIENCE-SLANT-MANIFEST.csv`, `AUDIENCE-SLANT-BACKBONE.md` |
| Handoff | `TECH-HANDOFF-FOR-CODY.md`, `CODY-VSCODE-IMPORT-RUNBOOK.md`, `CODY-HANDOFF-TOPIC-MATCHER.md`, `CODY-HANDOFF-CONVERSATION-BRANCHES.md` |
| Launch | `QUIZ-LAUNCH-PLAYBOOK.md` (14-day timeline) |
| Program design | `program-outline.md`, `GUIDE-REQUIREMENTS-STANDARD.md`, `NICHES-STRATEGY-KB.md` |
| Business | `affiliate-program.md`, `marketing-strategy.md`, `lead-magnet.md` |

---

### Marketing & Outreach — 8 files

| File | Purpose |
|------|---------|
| `marketing/tiktok-launch-calendar.md` | 28-day Month 1 calendar (2 posts/day) + Month 2 strategy |
| `marketing/tiktok-scripts/video-script-templates.md` | 8 video script templates (myth-busting, script comparison, etc.) |
| `marketing/creator-pitches-PLANNING.md` | Creator partnership planning |
| `marketing/affiliate/INFLUENCER-STRATEGY.md` | Influencer targeting and outreach strategy |
| `marketing/affiliate/COMPENSATION-STRUCTURE.md` | Commission rates and tiers |
| `marketing/affiliate/cold-dm-templates.md` | Ready-to-send DM scripts |
| `marketing/affiliate/email-pitch-templates.md` | Ready-to-send email pitches |
| `marketing/affiliate/creator-one-pager.md` | One-page creator partnership overview |

---

### Email & SMS Automation

| File | Purpose |
|------|---------|
| `email-sms/post-quiz-automations.md` | 5 email sequences (one per risk level) + 4-week SMS check-in content |
| `landing-page/quiz-landing-page.md` | Full quiz landing page copy: hero, 8 conversion sections, A/B test versions |

---

### Build & QA Scripts — 20 scripts

| Script | Purpose |
|--------|---------|
| `scripts/full_workspace_audit.py` | **9-category integrity audit** — file counts, voice sampling, quiz references, audience coverage, scoring/safety, product alignment, manifest sync, known gaps, placeholder/secret scan |
| `scripts/extract_worksheets.py` | Extract standalone worksheets from all guides |
| `scripts/generate_audience_slants.py` | Generate 1,343 audience-specific guide variants |
| `scripts/voice_contractions_pass.py` | Automated voice pass for contractions |
| `scripts/voice_pass_2.py` | Second voice pass (openers, action plans, diversification) |
| `scripts/fix_disclaimers.py` | Scan all files for missing disclaimers |
| `scripts/draft_all_guides.sh` | Batch guide drafting |
| `scripts/editorial_pass.py` | Editorial quality pass |
| `scripts/audit_quiz_deep.py` | Deep quiz reference validation |
| `scripts/audit_quiz_refs.py` | Quiz cross-reference checker |
| `scripts/build_architecture_assets.py` | Generate architecture config files |
| Other scripts | Chapter scaffolding, metadata fixes, manifest repairs |

---

## End-to-End User Flow

```
TikTok video (with UTM link)
  → Quiz landing page
    → 10-question scored quiz
      → Immediate results page (risk-band specific)
        → [low/moderate] Topic matcher (3 questions → matched guide)
          → [low/moderate] Audience matcher (identity/context → audience variant)
            → Recommendation stack (guide + offer lane + crisis resources)
              → Optional email/SMS capture
                → Stripe checkout (if purchasing)
                  → Webhook → fulfillment (email delivery, SMS enrollment)
                    → Post-quiz email sequence (risk-personalized)
                    → Check On Me SMS (weekly, 4 weeks + recurring)
```

**Critical safety rule:** For `critical` risk results, crisis resources (988, Crisis Text Line, 911) display first and prominently. Paid products are never primary. Contact capture cannot appear before crisis actions.

---

## VS Code Setup Instructions

### 1. Open the workspace

```bash
# Navigate to wherever you extracted the workspace
cd path/to/tiktok-mental-health
code .
```

### 2. Read orientation files (in order)

Open and read these files first — they are your source of truth:

1. `planning/CODY-VSCODE-IMPORT-RUNBOOK.md` — start here
2. `planning/TECH-HANDOFF-FOR-CODY.md` — full implementation spec
3. `planning/QUIZ-IMPLEMENTATION-CONTRACT.md` — scoring/routing rules
4. `web/api/README.md` — API scaffold guide

### 3. Install frontend dependencies

The Next.js app already exists in `web/`. No need to create-next-app.

```bash
cd web
npm install
```

### 4. Set up environment variables

The API routes already live at `web/api/`. An env template is at `web/.env.local` with all 18 variables documented. Fill in your real keys:

```bash
# Edit the existing template
open web/.env.local
```

See the provisioning checklist in `CODY-START-HERE.md` for which services to set up.

### 5. Apply Supabase migrations

```bash
# Option A: Supabase CLI (if using hosted Supabase)
supabase db push

# Option B: Run SQL directly in Supabase dashboard → SQL Editor
# Paste contents of these files in order:
#   supabase/migrations/20260320153000_backend_architecture.sql
#   supabase/migrations/20260320160000_rls_policies.sql
```

### 6. Run the workspace audit

```bash
python3 scripts/full_workspace_audit.py
```

Expected result: **0 CRITICAL, 0 WARNING, 2 INFO** (stale handoff doc references — cosmetic only).

### 7. Verify Stripe test mode

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Login and forward webhooks to local
stripe login
stripe listen --forward-to localhost:3000/api/webhooks/stripe
```

### 8. Start development

```bash
cd web
npm run dev
```

Test each route in order:
1. `POST /api/quiz/score` — verify scoring and risk bands
2. `POST /api/quiz/topic-match` — verify topic resolution
3. `POST /api/quiz/audience-match` — verify audience bucket assignment
4. `POST /api/quiz/recommendation` — verify full recommendation stack
5. `POST /api/checkout/session` — verify Stripe session creation
6. `POST /api/webhooks/stripe` — verify with `stripe trigger checkout.session.completed`
7. `POST /api/analytics/event` — verify event logging

---

## Source-of-Truth Reference

When files conflict, use this precedence:

| Domain | Source of truth |
|--------|----------------|
| API behavior & request/response | `planning/API-ROUTE-SPECS.md` + `quiz/api-contracts.json` |
| Database schema | `planning/BACKEND-SYSTEM-CONTRACT.md` + `supabase/migrations/` |
| Scoring & safety rules | `planning/QUIZ-IMPLEMENTATION-CONTRACT.md` |
| Product rules & routing | `quiz/recommendation-routing-config.json` |
| Guide catalog & offer mapping | `quiz/base-guide-catalog.json` + `planning/GUIDE-OFFER-MAPPING.csv` |
| Audience resolution | `quiz/audience-bucket-flow.json` + `planning/AUDIENCE-SLANT-MANIFEST.csv` |
| Fulfillment logic | `quiz/fulfillment-config.json` |
| Implementation scaffolds | `web/api/` |

---

## Product & Pricing

| Product | Price | Type |
|---------|-------|------|
| Ask Anyway Guide | $9 | One-time (single topic guide, audience-matched) |
| Ask Anyway Kit | $19 | One-time (multi-guide bundle) |
| Check On Me SMS | $4.99/mo | Subscription (weekly check-in texts) |
| Ask Anyway Bundle | $34 | One-time (guide + kit + 1 month SMS) |

---

## Safe Messaging Commitment

All content follows safe messaging guidelines from AFSP, SAMHSA, JED Foundation, and 988 Suicide & Crisis Lifeline standards. Content does not sensationalize, glamorize, or provide method details. Crisis resources (988, Crisis Text Line) are embedded in every content file and on every quiz result page.

---

## Content Production Status

- [x] 79 base topic guides — written, voice-passed, disclaimed
- [x] 1,343 audience variants — generated across 17 buckets
- [x] 2,686 standalone worksheets — extracted, audience-matched
- [x] Module 1: Why You Don't Ask — written
- [x] Module 2: Seeing the Opening — written
- [x] Module 3: The Words — written
- [x] Lead magnet content — written
- [x] Quiz questions + scoring — complete (10 JSON configs)
- [x] API route scaffolds — 7 endpoints, TypeScript, App Router
- [x] Supabase migrations — schema + RLS policies
- [x] Landing page copy — written
- [x] Email/SMS automations — 5 sequences + 4-week SMS content
- [x] TikTok launch calendar — 28-day Month 1 + Month 2
- [x] Influencer outreach pack — strategy, DMs, pitches, one-pager, compensation
- [x] Full workspace audit — passing clean (0 critical, 0 warnings)
- [x] Root web app shell — Next.js app scaffolded in `web/` with route wrappers and quiz page
- [ ] Stripe product setup — needs live price IDs
- [ ] Email/SMS provider verification — SendGrid/Twilio credentials and live webhook replay still needed
- [ ] Frontend refinement — quiz wizard works end-to-end but still needs visual/product polish
- [ ] Platform selected (Teachable / Kajabi / Gumroad / Stan Store)
- [ ] Launch
