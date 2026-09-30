-- Manual override for the beta/beta-v2 admin badge, for the rare case someone's
-- submission timestamp landed on the wrong side of BETA_V2_START. Applied directly
-- via Supabase MCP on 2026-09-08; this file documents it for the repo.
alter table assessment_responses
  add column if not exists cohort_override text check (cohort_override in ('beta', 'beta_v2'));

-- 2026-09-30: third cohort (beta v3) for submissions after the 29 Sept rebuild.
alter table assessment_responses drop constraint if exists assessment_responses_cohort_override_check;
alter table assessment_responses add constraint assessment_responses_cohort_override_check check (cohort_override in ('beta', 'beta_v2', 'beta_v3'));
