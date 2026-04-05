# API Handler Scaffold: Next.js App Router

Date: 2026-03-20  
Status: Ready for integration

## What this is

These are implementation-ready TypeScript handlers for every route defined in
`planning/API-ROUTE-SPECS.md`. They follow Next.js App Router conventions:
each `route.ts` exports a `POST()` function that receives a `Request` and
returns a `Response`.

The root `web/` folder now also includes a minimal Next.js app shell under
`web/app/` with wrapper routes that re-export these handlers, so the scaffold
can run in-place once Node tooling and env vars are available.

---

## File structure

```
web/api/
├── _lib/
│   ├── types.ts          : TypeScript types for all request/response shapes
│   ├── supabase.ts       : Supabase server client factory (service-role)
│   └── scorer.ts         : Quiz scoring and validation logic
├── quiz/
│   ├── score/route.ts            : POST /api/quiz/score
│   ├── topic-match/route.ts      : POST /api/quiz/topic-match
│   ├── audience-match/route.ts   : POST /api/quiz/audience-match
│   └── recommendation/route.ts  : POST /api/quiz/recommendation
├── checkout/
│   └── session/route.ts          : POST /api/checkout/session
├── webhooks/
│   └── stripe/route.ts           : POST /api/webhooks/stripe
└── analytics/
  └── event/route.ts            : POST /api/analytics/event
```

---

## Required environment variables

```env
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_SERVICE_KEY=service_role_key_here

STRIPE_SECRET_KEY=sk_live_or_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_IDS={"guide":"price_xxx","kit":"price_yyy","sms":"price_zzz","bundle":"price_aaa"}

SENDGRID_API_KEY=SG.xxxxx
SENDGRID_FROM_EMAIL=hello@askanyway.co
SENDGRID_TEMPLATE_GUIDE_DELIVERY=d-xxxxxxxxxxxxxxxx
SENDGRID_TEMPLATE_KIT_DELIVERY=d-yyyyyyyyyyyyyyyy
SENDGRID_POST_PURCHASE_LIST_ID=optional_list_id

TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_FROM_NUMBER=+1xxxxxxxxxx

CCE_BACKEND_URL=http://localhost:8000
```

---

## Required npm packages

```bash
npm install @supabase/supabase-js stripe
```

---

## Current status

### `quiz/topic-match/route.ts`
Config-driven matcher is implemented against `quiz/topic-matcher-flow.json` and
`quiz/topic-catalog.json`.

### `quiz/recommendation/route.ts`
Guide titles, offer lanes, and audience variant paths are resolved from
`quiz/base-guide-catalog.json`.

### `webhooks/stripe/route.ts`
SendGrid and Twilio dispatch code is implemented. Runtime verification still
depends on valid provider credentials and Stripe webhook replay.

### `analytics/event/route.ts`
Non-CTA events now persist to `analytics_events` in Supabase.

---

## Database

Apply migrations in order before running these handlers:
```
supabase/migrations/20260320153000_backend_architecture.sql
supabase/migrations/20260320160000_rls_policies.sql
supabase/migrations/20260402120000_analytics_events.sql
```

Schema reference: `planning/BACKEND-SYSTEM-CONTRACT.md`

---

## Fulfillment

Fulfillment actions per product are defined in `quiz/fulfillment-config.json`.
The webhook handler dispatches events based on `productFulfillmentMap` in that file.
Provider dispatch for SendGrid and Twilio is implemented in `web/api/webhooks/stripe/route.ts`.
Before launch, validate live credentials and webhook replay behavior in a real environment.

---

## Security reminders

- `SUPABASE_SERVICE_KEY` bypasses Row Level Security. Keep it server-side only.
  Apply RLS policies before going to production (see `supabase/policies/`
  once the auth layer is built).
- Stripe webhook signature verification is enforced in the webhook handler.
  Never skip it.
- Never expose `STRIPE_SECRET_KEY` to the browser.
