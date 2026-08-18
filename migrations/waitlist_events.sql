create table if not exists waitlist_events (
  id uuid primary key default gen_random_uuid(),
  event_type text not null,
  label text,
  locale text,
  source text,
  created_at timestamptz default now()
);

create index if not exists waitlist_events_event_type_idx on waitlist_events (event_type);
create index if not exists waitlist_events_created_at_idx on waitlist_events (created_at);
