-- Behavioral telemetry for the assessment flow: device type, break-panel
-- games/riddles played, and per-question pacing. One row per event; events
-- are sent while the assessment is still in progress (before a response_id
-- exists), then backfilled with response_id once the assessment is
-- submitted — see submit_assessment() in main.py. Sessions that never
-- complete simply keep response_id null, which is itself useful (drop-off
-- analysis), not an error case.
create table if not exists assessment_telemetry_events (
  id uuid primary key default gen_random_uuid(),
  session_id text not null,
  response_id uuid references assessment_responses(id) on delete set null,
  event_type text not null,      -- 'session_start' | 'question_view' | 'break_open' | 'break_activity'
  question_id text,              -- set on 'question_view' events
  activity_kind text,            -- set on 'break_open'/'break_activity' events: 'riddle' | 'tic_tac_toe' | 'rps' | 'memory_match'
  duration_ms integer,           -- set on 'question_view' events
  device_type text,              -- 'mobile' | 'desktop', set on 'session_start'
  locale text,
  payload jsonb,                 -- free-form extra detail, e.g. {"result": "win"} for a finished game
  created_at timestamptz default now()
);

create index if not exists assessment_telemetry_events_session_id_idx on assessment_telemetry_events (session_id);
create index if not exists assessment_telemetry_events_event_type_idx on assessment_telemetry_events (event_type);
create index if not exists assessment_telemetry_events_response_id_idx on assessment_telemetry_events (response_id);
create index if not exists assessment_telemetry_events_created_at_idx on assessment_telemetry_events (created_at);
