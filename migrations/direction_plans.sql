-- The direction a user chose to build their plan around (one of their suggested careers, or a field
-- they typed themselves), and the plan generated for it. One row per (response, direction); the row
-- flagged is_selected is the current choice. `plans` maps locale -> generated plan JSON ({"en": {...}, "ar": {...}})
-- so a user who switches language gets a plan generated once per language and then cached.
--
-- Applied to the production Supabase project on 2026-09-29 (table confirmed present, 0 rows). Only
-- GET/POST /assessment/{id}/direction and the PDF's best-effort "chosen direction" block read this table.

create table if not exists direction_plans (
  id uuid primary key default gen_random_uuid(),
  response_id uuid not null references assessment_responses(id) on delete cascade,
  direction_key text not null,              -- lower-cased, whitespace-collapsed label; dedupes repeat picks
  label text not null,                      -- what the user picked or typed (already sanitised)
  source text not null check (source in ('suggested', 'user')),
  plans jsonb not null default '{}'::jsonb,
  is_selected boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (response_id, direction_key)
);

create index if not exists direction_plans_response_id_idx on direction_plans (response_id);

-- Row level security: the production table has RLS enabled, like all other public tables (checked after applying).
-- The line below is what enables it; keep it so a fresh environment matches production.
alter table direction_plans enable row level security;
