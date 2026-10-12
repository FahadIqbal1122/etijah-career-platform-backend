-- Server-side copy of an in-progress assessment, so the "come back and finish" email link works from any
-- device. One row per browser session; the unguessable resume_token is the ONLY way to read a row back
-- (there is deliberately no lookup by email). Rows are deleted when the assessment is submitted
-- (submit_assessment() in main.py) or discarded ("Start fresh"), and ignored after 30 days.
create table if not exists assessment_drafts (
  id uuid primary key default gen_random_uuid(),
  resume_token text not null unique,
  email text not null,                          -- stored lowercased
  full_name text,
  locale text default 'en',
  answers jsonb not null default '{}'::jsonb,
  current_index int not null default 0,
  revealed_frameworks jsonb not null default '[]'::jsonb,
  total_questions int not null,
  created_at timestamptz not null default now(),
  last_activity_at timestamptz not null default now(),
  reminder_sent_at timestamptz                  -- set once the "continue" reminder has gone out
);

create index if not exists assessment_drafts_email_idx on assessment_drafts (email);
create index if not exists assessment_drafts_last_activity_idx on assessment_drafts (last_activity_at);

-- Same lockdown as the 4 Oct fix: RLS on with no policies and no grants to the public keys.
-- Only the backend (service-role key) can read or write this table.
alter table assessment_drafts enable row level security;
revoke all on assessment_drafts from anon, authenticated;
