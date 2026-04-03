create table if not exists public.analytics_events (
  id uuid primary key default gen_random_uuid(),
  quiz_session_id uuid not null references public.quiz_sessions(id) on delete cascade,
  event_name text not null,
  payload_json jsonb,
  event_timestamp timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create index if not exists idx_analytics_events_quiz_session_id on public.analytics_events (quiz_session_id);
create index if not exists idx_analytics_events_event_name on public.analytics_events (event_name);
create index if not exists idx_analytics_events_event_timestamp on public.analytics_events (event_timestamp desc);

alter table public.analytics_events enable row level security;

comment on table public.analytics_events is 'RLS enabled. Internal analytics events written by API handlers only.';