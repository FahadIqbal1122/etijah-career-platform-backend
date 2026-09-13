-- Students track (majors guidance + exposure ideas) per the beta-strategy doc's
-- "three practical tracks" requirement. Not tier-gated (free for everyone,
-- like internships) since this replaces job listings for still-enrolled
-- students rather than being an upsell — see STILL_ENROLLED_STAGES.
alter table assessment_responses
  add column if not exists student_track_cache jsonb,
  add column if not exists student_track_cache_ar jsonb;
