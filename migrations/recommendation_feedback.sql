-- Why a user rejected one of their recommended careers (results page: "Not for me" on a career card).
-- One row per (assessment, career title); choosing another reason replaces it, "Undo" deletes it.
-- Read only by GET/POST/DELETE /assessment/{id}/recommendation-feedback and the admin summary; it does not
-- affect any score or report content.
--
-- Applied to the production Supabase project on 2026-09-29 (table confirmed present, 0 rows, row level security on).

create table if not exists recommendation_feedback (
  id uuid primary key default gen_random_uuid(),
  response_id uuid not null references assessment_responses(id) on delete cascade,
  career_title text not null,               -- as shown to the user (so it is in their language)
  locale text not null default 'en',
  reason text not null check (reason in ('uninterested', 'unqualified', 'unfamiliar', 'impractical')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (response_id, career_title)
);

create index if not exists recommendation_feedback_response_id_idx on recommendation_feedback (response_id);
create index if not exists recommendation_feedback_reason_idx on recommendation_feedback (reason);

-- Every other public table has row level security on (checked 2026-09-29); the backend reads and writes this one.
alter table recommendation_feedback enable row level security;
