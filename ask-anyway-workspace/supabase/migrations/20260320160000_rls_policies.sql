-- ─────────────────────────────────────────────────────────────────────────────
-- RLS Policies for the quiz platform backend
-- Source of truth: planning/BACKEND-SYSTEM-CONTRACT.md
-- Auth model:
--   All writes and reads originate from server-side API handlers using the
--   Supabase service_role key, which bypasses RLS by default.
--   RLS is enabled on every table as a defense-in-depth measure so that
--   accidental client exposure or future auth changes cannot leak data.
--
--   Policy summary:
--   - No direct client access to any table.
--   - service_role (used by API handlers) bypasses RLS automatically.
--   - Authenticated users (Supabase auth JWT) have no direct table access
--     until an explicit read policy is added (e.g., an admin dashboard).
--   - Anonymous users are fully denied on all tables.
-- ─────────────────────────────────────────────────────────────────────────────

-- ── Enable RLS on all tables ──────────────────────────────────────────────────

alter table public.leads                   enable row level security;
alter table public.quiz_sessions           enable row level security;
alter table public.topic_match_sessions    enable row level security;
alter table public.audience_match_sessions enable row level security;
alter table public.guide_recommendations   enable row level security;
alter table public.product_clicks          enable row level security;
alter table public.purchases               enable row level security;
alter table public.fulfillment_events      enable row level security;

-- ── No-access baseline ───────────────────────────────────────────────────────
-- By enabling RLS with no permissive policies, all roles other than
-- service_role are denied by default. No explicit DENY policy is needed.

-- ─────────────────────────────────────────────────────────────────────────────
-- FUTURE: Admin dashboard read access
--
-- If you add an internal Supabase Auth user for a dashboard, add policies like:
--
--   create policy "admin can read leads"
--     on public.leads
--     for select
--     to authenticated
--     using (auth.jwt() ->> 'role' = 'admin');
--
-- Replace 'admin' with whatever role claim you assign in the Supabase dashboard.
-- Do not grant write access to the dashboard role — all writes go through
-- the server-side API handlers.
-- ─────────────────────────────────────────────────────────────────────────────

-- ── Comment ───────────────────────────────────────────────────────────────────
comment on table public.leads
  is 'RLS enabled. Write access via service_role (API handlers) only.';
comment on table public.quiz_sessions
  is 'RLS enabled. Write access via service_role (API handlers) only.';
comment on table public.topic_match_sessions
  is 'RLS enabled. Write access via service_role (API handlers) only.';
comment on table public.audience_match_sessions
  is 'RLS enabled. Write access via service_role (API handlers) only.';
comment on table public.guide_recommendations
  is 'RLS enabled. Write access via service_role (API handlers) only.';
comment on table public.product_clicks
  is 'RLS enabled. Write access via service_role (API handlers) only.';
comment on table public.purchases
  is 'RLS enabled. Write access via service_role (API handlers) only.';
comment on table public.fulfillment_events
  is 'RLS enabled. Write access via service_role (API handlers) only.';
