# Backend System Contract

Date: 2026-03-20
Status: Locked architecture and persistence contract before additional guide drafting.

## Purpose

This document defines the backend architecture needed to support:
- quiz scoring
- topic matching
- audience bucket matching
- guide recommendation
- offer-lane selection
- purchase and fulfillment tracking
- follow-up automation

## Source-of-Truth Files

Core flow and content system:
- quiz/topic-matcher-flow.json
- quiz/audience-bucket-flow.json
- quiz/conversation-branch-flow.json
- quiz/base-guide-catalog.json
- quiz/product-catalog.json
- quiz/recommendation-routing-config.json
- quiz/api-contracts.json
- planning/GUIDE-OFFER-MAPPING.csv
- planning/AUDIENCE-SLANT-MANIFEST.csv
- planning/API-ROUTE-SPECS.md
- supabase/migrations/20260320153000_backend_architecture.sql

## Core Entities

### 1. leads

Represents a person who starts or completes the quiz.

Required fields:
- id
- email
- phone
- first_name
- utm_source
- utm_medium
- utm_campaign
- utm_content
- utm_term
- email_opted_in
- sms_opted_in
- created_at
- updated_at

### 2. quiz_sessions

Represents one quiz run from start to completion.

Required fields:
- id
- lead_id
- started_at
- completed_at
- total_score
- risk_level
- override_triggered
- answers_by_question_json
- quiz_version
- landing_path
- result_path

### 3. topic_match_sessions

Stores topic matcher answers and recommendations.

Required fields:
- id
- quiz_session_id
- matcher_version
- tm_q1_option_id
- tm_q2_option_id
- tm_q3_option_ids_json
- matched_domain
- recommended_guide_ids_json
- recommended_offer_type
- created_at

### 4. audience_match_sessions

Stores audience-lens selection and primary bucket choice.

Required fields:
- id
- quiz_session_id
- matcher_version
- selected_identity_bucket_ids_json
- selected_context_bucket_ids_json
- selected_bucket_ids_json
- primary_bucket_id
- overlay_bucket_ids_json
- created_at

### 5. guide_recommendations

Stores the final recommendation state shown to the user.

Required fields:
- id
- quiz_session_id
- topic_match_session_id
- audience_match_session_id
- base_guide_id
- audience_variant_path
- primary_offer_id
- secondary_offer_id
- bundle_role
- why_matched_json
- created_at

### 6. product_clicks

Tracks CTA engagement.

Required fields:
- id
- quiz_session_id
- guide_recommendation_id
- product_id
- click_location
- clicked_at

### 7. purchases

Tracks transactions and fulfillment state.

Required fields:
- id
- lead_id
- quiz_session_id
- product_id
- guide_id
- audience_bucket_id
- amount_cents
- currency
- stripe_session_id
- stripe_payment_intent_id
- purchased_at
- fulfillment_status

### 8. fulfillment_events

Tracks delivery of digital assets and automations.

Required fields:
- id
- purchase_id
- event_type
- event_payload_json
- sent_at
- provider
- provider_message_id

## Recommended Database Tables (Supabase/Postgres)

Executable migration file:
- supabase/migrations/20260320153000_backend_architecture.sql

```sql
create table leads (
  id uuid primary key default gen_random_uuid(),
  email text unique,
  phone text,
  first_name text,
  utm_source text,
  utm_medium text,
  utm_campaign text,
  utm_content text,
  utm_term text,
  email_opted_in boolean default false,
  sms_opted_in boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table quiz_sessions (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid references leads(id),
  started_at timestamptz default now(),
  completed_at timestamptz,
  total_score integer,
  risk_level text,
  override_triggered boolean default false,
  answers_by_question_json jsonb not null,
  quiz_version text,
  landing_path text,
  result_path text
);

create table topic_match_sessions (
  id uuid primary key default gen_random_uuid(),
  quiz_session_id uuid references quiz_sessions(id),
  matcher_version text,
  tm_q1_option_id text,
  tm_q2_option_id text,
  tm_q3_option_ids_json jsonb,
  matched_domain text,
  recommended_guide_ids_json jsonb,
  recommended_offer_type text,
  created_at timestamptz default now()
);

create table audience_match_sessions (
  id uuid primary key default gen_random_uuid(),
  quiz_session_id uuid references quiz_sessions(id),
  matcher_version text,
  selected_identity_bucket_ids_json jsonb,
  selected_context_bucket_ids_json jsonb,
  selected_bucket_ids_json jsonb,
  primary_bucket_id text,
  overlay_bucket_ids_json jsonb,
  created_at timestamptz default now()
);

create table guide_recommendations (
  id uuid primary key default gen_random_uuid(),
  quiz_session_id uuid references quiz_sessions(id),
  topic_match_session_id uuid references topic_match_sessions(id),
  audience_match_session_id uuid references audience_match_sessions(id),
  base_guide_id text,
  audience_variant_path text,
  primary_offer_id text,
  secondary_offer_id text,
  bundle_role text,
  why_matched_json jsonb,
  created_at timestamptz default now()
);

create table product_clicks (
  id uuid primary key default gen_random_uuid(),
  quiz_session_id uuid references quiz_sessions(id),
  guide_recommendation_id uuid references guide_recommendations(id),
  product_id text,
  click_location text,
  clicked_at timestamptz default now()
);

create table purchases (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid references leads(id),
  quiz_session_id uuid references quiz_sessions(id),
  product_id text,
  guide_id text,
  audience_bucket_id text,
  amount_cents integer,
  currency text default 'USD',
  stripe_session_id text,
  stripe_payment_intent_id text,
  purchased_at timestamptz default now(),
  fulfillment_status text default 'pending'
);

create table fulfillment_events (
  id uuid primary key default gen_random_uuid(),
  purchase_id uuid references purchases(id),
  event_type text,
  event_payload_json jsonb,
  sent_at timestamptz default now(),
  provider text,
  provider_message_id text
);
```

## API Contract

### POST /api/quiz/score

Input:
- answers_by_question
- utm values
- lead identity if known

Output:
- total_score
- risk_level
- override_triggered
- result_screen_id
- allow_topic_matcher
- allow_audience_matcher

### POST /api/quiz/topic-match

Input:
- quiz_session_id
- tm_q1
- tm_q2
- tm_q3

Output:
- matched_domain
- recommended_guide_ids
- recommended_offer_type

### POST /api/quiz/audience-match

Input:
- quiz_session_id
- ab_q1 selections
- ab_q2 selections
- primary_bucket_id

Output:
- primary_bucket_id
- overlay_bucket_ids
- fallback_used

### POST /api/quiz/recommendation

Input:
- quiz_session_id
- topic_match_session_id
- audience_match_session_id

Output:
- base_guide_id
- audience_variant_path
- primary_offer_id
- secondary_offer_id
- crisis_resources_visible
- why_matched

### POST /api/checkout/session

Input:
- lead_id
- quiz_session_id
- guide_id
- audience_bucket_id
- product_id

Output:
- stripe_checkout_url
- purchase_intent_record_id

### POST /api/webhooks/stripe

Behavior:
- validate stripe signature
- mark purchase paid
- trigger asset fulfillment
- trigger email or sms follow-up if applicable

## Recommendation Selection Logic

1. Score quiz and assign risk level.
2. If critical, skip paid recommendation flow and show crisis resources.
3. If allowed, run topic matcher and get top 3 guide candidates.
4. If allowed, run audience matcher and resolve one primary bucket plus overlays.
5. Select the best base guide from topic matching.
6. Convert base guide to audience-specific path using primary bucket.
7. Pull offer lane from GUIDE-OFFER-MAPPING.csv or quiz/base-guide-catalog.json.
8. Render primary offer plus secondary offer.
9. Persist recommendation event and analytics payload.

## Fulfillment Rules

Guide:
- deliver one audience-specific guide file or equivalent rendered asset

Kit:
- deliver guide plus scripts/worksheets package

SMS:
- enroll in check-in automation if opted in and compliant

Bundle:
- deliver top matched guides plus optional sms upsell

Critical:
- never place paid content above crisis support
- allow capture only after crisis resources are shown

## Backend Completion Definition

Architecture is complete when:
- all source-of-truth config files exist
- all API contracts are documented
- all persistence entities are defined
- all guide IDs map to an offer lane
- all audience variants map from a stable base guide path
- Cody can build without guessing how scoring, matching, and fulfillment connect
