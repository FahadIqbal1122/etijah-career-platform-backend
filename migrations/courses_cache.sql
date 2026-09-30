-- Cached AI course picks per assessment (English and Arabic). Applied 30 Sep 2026.
alter table public.assessment_responses
  add column if not exists courses_cache jsonb,
  add column if not exists courses_cache_ar jsonb;
