-- Admin-configurable email scheduler: schedule a seeded email_templates row to go
-- out later, either to one recipient or to a named segment (e.g. beta signups who
-- haven't finished the assessment). A VPS crontab hits
-- POST /internal/jobs/send-scheduled-emails every few minutes to actually send
-- whatever is due — see main.py for that endpoint and the segment definitions.
create table if not exists scheduled_emails (
  id uuid primary key default gen_random_uuid(),
  template_key text not null references email_templates(key),
  recipient_type text not null check (recipient_type in ('single', 'segment')),
  recipient_email text,
  recipient_name text,
  -- Valid values are enforced in app code (main.py: SEGMENT_KEYS), not here —
  -- keeps adding a new named segment a one-file change, not a migration.
  segment_key text,
  locale text not null default 'en',
  variables jsonb not null default '{}'::jsonb,
  scheduled_for timestamptz not null,
  status text not null default 'pending' check (status in ('pending', 'sending', 'sent', 'failed', 'cancelled')),
  sent_count int not null default 0,
  failed_count int not null default 0,
  error text,
  created_at timestamptz not null default now(),
  sent_at timestamptz
);

create index if not exists scheduled_emails_due_idx on scheduled_emails (scheduled_for) where status = 'pending';
