create table if not exists bug_reports (
  id uuid primary key default gen_random_uuid(),
  source text not null check (source in ('user', 'system')),
  status text not null default 'open' check (status in ('open', 'resolved')),
  description text,
  feature text,
  error_type text,
  error_message text,
  stack_trace text,
  response_id uuid references assessment_responses(id) on delete set null,
  full_name text,
  email text,
  locale text,
  country text,
  device_type text,
  page text,
  user_agent text,
  created_at timestamptz default now()
);

create index if not exists bug_reports_source_idx on bug_reports (source);
create index if not exists bug_reports_status_idx on bug_reports (status);
create index if not exists bug_reports_created_at_idx on bug_reports (created_at);
create index if not exists bug_reports_response_id_idx on bug_reports (response_id);
