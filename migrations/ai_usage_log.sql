-- One row per Gemini / Claude call (see ai_usage.py): what it cost and what caused it.
create table if not exists ai_usage_log (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz default now(),
  provider text not null,          -- gemini | claude
  model text,
  kind text,                       -- report | coach_chat | coach_paid | embed | transcript_chunk
  label text,                      -- e.g. content:narrative, translate:ar, coach:landing
  endpoint text,                   -- request path with ids replaced, e.g. /assessment/{id}/ai-impact
  response_id text,                -- the assessment the call was for, when known
  client_ip text,
  input_tokens int default 0,      -- billed input, cached tokens excluded
  cached_tokens int default 0,
  output_tokens int default 0,     -- billed output, thinking tokens included
  thinking_tokens int default 0,   -- already inside output_tokens (Gemini 2.5 thinking)
  est_cost_usd numeric(10,5) default 0,
  seconds numeric(8,2),
  ok boolean default true,
  error text
);

create index if not exists ai_usage_log_created_at_idx on ai_usage_log (created_at);
create index if not exists ai_usage_log_response_id_idx on ai_usage_log (response_id);

-- Written with the service key only; nobody reads it through the public API.
alter table ai_usage_log enable row level security;
