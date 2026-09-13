-- Remaining two practical tracks from the beta-strategy doc: "entering the
-- market" (certifications — entry roles/employers already exist as jobs/
-- companies) and "working professionals" (progression/transition write-up).
-- Same shape as student_track_cache: not tier-gated, free for everyone in
-- the relevant current_stage.
alter table assessment_responses
  add column if not exists certifications_cache jsonb,
  add column if not exists certifications_cache_ar jsonb,
  add column if not exists career_path_cache jsonb,
  add column if not exists career_path_cache_ar jsonb;
