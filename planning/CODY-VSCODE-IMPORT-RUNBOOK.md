# Ask Anyway - Cody VS Code Import Runbook

Prepared: 2026-03-20
Audience: Cody (implementation owner)
Purpose: Single starting file to import, understand, and execute the current build state without ambiguity.

---

## 1) What Is Already Built

This workspace already contains the following completed work:

- Product and pricing locked:
  - Ask Anyway
  - $9 single guide
  - $19 guide kit
  - $4.99 monthly SMS
  - $34 bundle
- Backend architecture and contracts complete:
  - API route contracts and scaffolded handlers
  - Supabase schema migration
  - RLS migration (service-role server access pattern)
  - Stripe webhook skeleton with config-driven fulfillment dispatch
- Recommendation and fulfillment configuration complete:
  - Product and routing config JSON files
  - Fulfillment map by product ID
- Content pipeline status:
  - Base architecture and audience slant manifests in place
  - Audience variant support-step placeholders already replaced across all generated files
- Influencer outreach pack complete:
  - Strategy
  - Compensation model
  - Cold DMs
  - Email pitches
  - Creator one-pager

---

## 2) Open These Files First (In Order)

1. planning/CODY-VSCODE-IMPORT-RUNBOOK.md
2. planning/TECH-HANDOFF-FOR-CODY.md
3. web/api/README.md
4. planning/API-ROUTE-SPECS.md
5. planning/BACKEND-SYSTEM-CONTRACT.md
6. quiz/api-contracts.json
7. quiz/recommendation-routing-config.json
8. supabase/migrations/20260320153000_backend_architecture.sql
9. supabase/migrations/20260320160000_rls_policies.sql
10. quiz/fulfillment-config.json

If anything in older notes conflicts with this list, this list wins.

---

## 3) Current Source of Truth by Domain

- API behavior and request/response contracts:
  - planning/API-ROUTE-SPECS.md
  - quiz/api-contracts.json
- Database tables and persistence model:
  - planning/BACKEND-SYSTEM-CONTRACT.md
  - supabase/migrations/20260320153000_backend_architecture.sql
- Authorization and write posture:
  - supabase/migrations/20260320160000_rls_policies.sql
- Recommendation and offer resolution:
  - quiz/recommendation-routing-config.json
  - quiz/base-guide-catalog.json
  - planning/GUIDE-OFFER-MAPPING.csv
  - planning/AUDIENCE-SLANT-MANIFEST.csv
- Fulfillment logic map:
  - quiz/fulfillment-config.json
- Implemented route scaffolds:
  - web/api/

---

## 4) Required API Surface (Do Not Collapse)

Maintain these endpoints as separate stages:

- POST /api/quiz/score
- POST /api/quiz/topic-match
- POST /api/quiz/audience-match
- POST /api/quiz/recommendation
- POST /api/checkout/session
- POST /api/webhooks/stripe
- POST /api/analytics/event

Do not replace with a legacy single POST /api/quiz primary flow.

---

## 5) Environment Setup Checklist

In the Next.js runtime environment, set:

- SUPABASE_URL
- SUPABASE_SERVICE_KEY
- STRIPE_SECRET_KEY
- STRIPE_WEBHOOK_SECRET
- STRIPE_PRICE_IDS as JSON map by product id

Install required packages:

- @supabase/supabase-js
- stripe

---

## 6) Known TODOs Before Production

These are intentionally scaffolded and must be completed:

1. quiz/topic-match route domain matcher
- Replace stub match function with config-driven matching using quiz/topic-matcher-flow.json.

2. quiz/recommendation route title resolver
- Resolve human-readable guide title from quiz/base-guide-catalog.json instead of echoing guide id.

3. Stripe webhook fulfillment providers
- Implement provider calls for:
  - guide or kit delivery email
  - SMS enrollment
  - email sequence trigger

4. Analytics routing
- Non-CTA events currently log only; persist to analytics store if needed.

5. Frontend integration
- Wire app pages to call all staged endpoints in sequence and handle critical fast-path safely.

---

## 7) Recommended VS Code Startup Flow for Cody

1. Open workspace root in VS Code.
2. Read sections 2 and 3 of this file.
3. Open a terminal at workspace root.
4. Confirm migration files and API scaffold exist in expected paths.
5. Create a short implementation branch.
6. Apply and validate Supabase migrations in order.
7. Integrate web/api handlers into target Next.js app/api structure.
8. Set environment variables and test route-by-route locally.
9. Wire webhook with Stripe test mode and replay sample events.
10. Record any contract deviations in a change log file before edits land.

---

## 8) Suggested Prompt for Cody to Paste Into Copilot Chat

Use this exact prompt at workspace open:

"Read and follow this implementation order exactly:
1) planning/CODY-VSCODE-IMPORT-RUNBOOK.md
2) planning/TECH-HANDOFF-FOR-CODY.md
3) web/api/README.md
4) planning/API-ROUTE-SPECS.md
5) planning/BACKEND-SYSTEM-CONTRACT.md
6) quiz/api-contracts.json
7) quiz/recommendation-routing-config.json
8) supabase/migrations/20260320153000_backend_architecture.sql
9) supabase/migrations/20260320160000_rls_policies.sql
10) quiz/fulfillment-config.json

Then summarize:
- required implementation tasks
- unresolved TODOs
- exact local run steps
- migration order and validation plan
- any contract inconsistencies found

Do not redesign architecture. Preserve staged API flow and existing table model."

---

## 9) Influencer Package Location (Already Prepared)

For non-engineering handoff and launch ops:

- marketing/affiliate/INFLUENCER-STRATEGY.md
- marketing/affiliate/COMPENSATION-STRUCTURE.md
- marketing/affiliate/cold-dm-templates.md
- marketing/affiliate/email-pitch-templates.md
- marketing/affiliate/creator-one-pager.md

---

## 10) Delivery Recommendation to You (Sender)

When you send this to Cody, include:

- The zip archive created from this workspace handoff package.
- A one-line instruction: start at planning/CODY-VSCODE-IMPORT-RUNBOOK.md.
- The requested deadline and definition of done.
- Your preferred communication channel for blocker questions.

Keep one owner for contract edits to avoid drift.
