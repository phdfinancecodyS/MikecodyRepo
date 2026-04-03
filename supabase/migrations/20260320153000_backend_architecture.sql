-- Backend architecture migration
-- Source of truth: planning/BACKEND-SYSTEM-CONTRACT.md

create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.leads (
  id uuid primary key default gen_random_uuid(),
  email text unique,
  phone text,
  first_name text,
  utm_source text,
  utm_medium text,
  utm_campaign text,
  utm_content text,
  utm_term text,
  email_opted_in boolean not null default false,
  sms_opted_in boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create trigger set_leads_updated_at
before update on public.leads
for each row
execute function public.set_updated_at();

create table if not exists public.quiz_sessions (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid references public.leads(id) on delete set null,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  total_score integer check (total_score is null or (total_score >= 0 and total_score <= 30)),
  risk_level text check (
    risk_level is null or risk_level in ('low_risk', 'moderate_risk', 'high_risk', 'critical')
  ),
  override_triggered boolean not null default false,
  answers_by_question_json jsonb not null,
  quiz_version text,
  landing_path text,
  result_path text,
  created_at timestamptz not null default now()
);

create table if not exists public.topic_match_sessions (
  id uuid primary key default gen_random_uuid(),
  quiz_session_id uuid not null unique references public.quiz_sessions(id) on delete cascade,
  matcher_version text,
  tm_q1_option_id text,
  tm_q2_option_id text,
  tm_q3_option_ids_json jsonb,
  matched_domain text,
  recommended_guide_ids_json jsonb,
  recommended_offer_type text check (
    recommended_offer_type is null or recommended_offer_type in ('guide', 'kit', 'sms', 'bundle', 'free_crisis_resources')
  ),
  created_at timestamptz not null default now()
);

create table if not exists public.audience_match_sessions (
  id uuid primary key default gen_random_uuid(),
  quiz_session_id uuid not null unique references public.quiz_sessions(id) on delete cascade,
  matcher_version text,
  selected_identity_bucket_ids_json jsonb,
  selected_context_bucket_ids_json jsonb,
  selected_bucket_ids_json jsonb,
  primary_bucket_id text,
  overlay_bucket_ids_json jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.guide_recommendations (
  id uuid primary key default gen_random_uuid(),
  quiz_session_id uuid not null unique references public.quiz_sessions(id) on delete cascade,
  topic_match_session_id uuid references public.topic_match_sessions(id) on delete set null,
  audience_match_session_id uuid references public.audience_match_sessions(id) on delete set null,
  base_guide_id text not null,
  audience_variant_path text,
  primary_offer_id text not null check (
    primary_offer_id in ('guide', 'kit', 'sms', 'bundle', 'free_crisis_resources')
  ),
  secondary_offer_id text check (
    secondary_offer_id is null or secondary_offer_id in ('guide', 'kit', 'sms', 'bundle', 'free_crisis_resources')
  ),
  bundle_role text,
  why_matched_json jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.product_clicks (
  id uuid primary key default gen_random_uuid(),
  quiz_session_id uuid not null references public.quiz_sessions(id) on delete cascade,
  guide_recommendation_id uuid references public.guide_recommendations(id) on delete set null,
  product_id text not null check (
    product_id in ('guide', 'kit', 'sms', 'bundle', 'free_crisis_resources')
  ),
  click_location text,
  clicked_at timestamptz not null default now()
);

create table if not exists public.purchases (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid references public.leads(id) on delete set null,
  quiz_session_id uuid references public.quiz_sessions(id) on delete set null,
  product_id text not null check (
    product_id in ('guide', 'kit', 'sms', 'bundle', 'free_crisis_resources')
  ),
  guide_id text,
  audience_bucket_id text,
  amount_cents integer not null check (amount_cents >= 0),
  currency text not null default 'USD',
  stripe_session_id text unique,
  stripe_payment_intent_id text unique,
  purchased_at timestamptz not null default now(),
  fulfillment_status text not null default 'pending' check (
    fulfillment_status in ('pending', 'processing', 'fulfilled', 'failed', 'canceled')
  )
);

create table if not exists public.fulfillment_events (
  id uuid primary key default gen_random_uuid(),
  purchase_id uuid not null references public.purchases(id) on delete cascade,
  event_type text not null,
  event_payload_json jsonb,
  sent_at timestamptz not null default now(),
  provider text,
  provider_message_id text
);

create index if not exists idx_leads_created_at on public.leads (created_at desc);
create index if not exists idx_leads_utm_campaign on public.leads (utm_campaign);
create index if not exists idx_quiz_sessions_lead_id on public.quiz_sessions (lead_id);
create index if not exists idx_quiz_sessions_risk_level on public.quiz_sessions (risk_level);
create index if not exists idx_quiz_sessions_completed_at on public.quiz_sessions (completed_at);
create index if not exists idx_topic_match_sessions_domain on public.topic_match_sessions (matched_domain);
create index if not exists idx_audience_match_sessions_primary_bucket on public.audience_match_sessions (primary_bucket_id);
create index if not exists idx_guide_recommendations_base_guide_id on public.guide_recommendations (base_guide_id);
create index if not exists idx_guide_recommendations_primary_offer on public.guide_recommendations (primary_offer_id);
create index if not exists idx_product_clicks_quiz_session_id on public.product_clicks (quiz_session_id);
create index if not exists idx_product_clicks_product_id on public.product_clicks (product_id);
create index if not exists idx_purchases_lead_id on public.purchases (lead_id);
create index if not exists idx_purchases_quiz_session_id on public.purchases (quiz_session_id);
create index if not exists idx_purchases_product_id on public.purchases (product_id);
create index if not exists idx_purchases_fulfillment_status on public.purchases (fulfillment_status);
create index if not exists idx_fulfillment_events_purchase_id on public.fulfillment_events (purchase_id);
create index if not exists idx_fulfillment_events_event_type on public.fulfillment_events (event_type);

comment on table public.leads is 'People who start or complete the quiz, with capture and attribution metadata.';
comment on table public.quiz_sessions is 'One quiz run from start to finish, including score and risk band.';
comment on table public.topic_match_sessions is 'Post-quiz topic matcher answers and recommendation candidates.';
comment on table public.audience_match_sessions is 'Audience lens selections, primary bucket, and overlay buckets.';
comment on table public.guide_recommendations is 'Resolved guide, audience variant, and offer recommendation shown to the user.';
comment on table public.product_clicks is 'CTA and product click events from quiz or results flow.';
comment on table public.purchases is 'Checkout and payment records tied to guide and audience context.';
comment on table public.fulfillment_events is 'Digital delivery and automation events triggered after purchase.';
