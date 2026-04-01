# API Handler Scaffold — Next.js App Router

Date: 2026-03-20  
Status: Ready for integration

## What this is

These are implementation-ready TypeScript handlers for every route defined in
`planning/API-ROUTE-SPECS.md`. They follow Next.js App Router conventions:
each `route.ts` exports a `POST()` function that receives a `Request` and
returns a `Response`.

Drop the contents of `web/api/` into your Next.js project's `app/api/` folder.

---

## File structure

```
web/api/
├── _lib/
│   ├── types.ts          — TypeScript types for all request/response shapes
│   ├── supabase.ts       — Supabase server client factory (service-role)
│   └── scorer.ts         — Quiz scoring and validation logic
├── quiz/
│   ├── score/route.ts            — POST /api/quiz/score
│   ├── topic-match/route.ts      — POST /api/quiz/topic-match
│   ├── audience-match/route.ts   — POST /api/quiz/audience-match
│   └── recommendation/route.ts  — POST /api/quiz/recommendation
├── checkout/
│   └── session/route.ts          — POST /api/checkout/session
├── webhooks/
│   └── stripe/route.ts           — POST /api/webhooks/stripe
└── analytics/
    └── event/route.ts            — POST /api/analytics/event
```

---

## Required environment variables

```env
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_SERVICE_KEY=service_role_key_here

STRIPE_SECRET_KEY=sk_live_or_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_IDS={"guide":"price_xxx","kit":"price_yyy","sms":"price_zzz","bundle":"price_aaa"}
```

---

## Required npm packages

```bash
npm install @supabase/supabase-js stripe
```

---

## Where logic is incomplete (mark as TODO before launch)

### `quiz/topic-match/route.ts`
The `matchDomain()` function is a stub. Replace it with a config-driven
evaluation against `quiz/topic-matcher-flow.json`. The answer keys, option ids,
weighted domain mapping, and guide id lists are all defined there.

### `quiz/recommendation/route.ts`
`baseGuideTitle` returns the raw `base_guide_id`. Before launch, load the
human-readable title from `quiz/base-guide-catalog.json` by matching `guide_id`.

### `webhooks/stripe/route.ts`
Two delivery steps are marked `TODO` inside `fulfillPurchase()`:
- Email delivery (SendGrid / ConvertKit)
- SMS enrollment (compliance check required)

### `analytics/event/route.ts`
Non-CTA events are logged to stdout only. Route them to a dedicated analytics
table or third-party service (Mixpanel, PostHog, etc.) once decided.

---

## Database

Apply migrations in order before running these handlers:
```
supabase/migrations/20260320153000_backend_architecture.sql
supabase/migrations/20260320160000_rls_policies.sql
```

Schema reference: `planning/BACKEND-SYSTEM-CONTRACT.md`

---

## Fulfillment

Fulfillment actions per product are defined in `quiz/fulfillment-config.json`.
The webhook handler dispatches events based on `productFulfillmentMap` in that file.
Provider stubs are marked `TODO` in `web/api/webhooks/stripe/route.ts` and must be
wired to real SendGrid / ConvertKit / Twilio calls before launch.

---

## Security reminders

- `SUPABASE_SERVICE_KEY` bypasses Row Level Security. Keep it server-side only.
  Apply RLS policies before going to production (see `supabase/policies/`
  once the auth layer is built).
- Stripe webhook signature verification is enforced in the webhook handler.
  Never skip it.
- Never expose `STRIPE_SECRET_KEY` to the browser.
