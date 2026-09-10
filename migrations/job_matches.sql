-- main.py's /internal/jobs/refresh-matches cron endpoint and /jobs/my-matches
-- (Launchpad tier only) both read/write a `job_matches` table that was never
-- created — every call fails with PGRST205 "Could not find the table
-- 'public.job_matches' in the schema cache" (9 open bug_reports rows,
-- feature=unhandled_exception, page=/jobs/my-matches, since 2026-09-09).
create table if not exists job_matches (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  response_id uuid not null references assessment_responses(id) on delete cascade,
  job_data jsonb not null,
  matched_at timestamptz not null default now()
);

create index if not exists job_matches_user_id_idx on job_matches (user_id);
create index if not exists job_matches_matched_at_idx on job_matches (matched_at);
