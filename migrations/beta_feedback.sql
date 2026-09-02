create table if not exists beta_feedback (
  id uuid primary key default gen_random_uuid(),
  response_id uuid not null references assessment_responses(id) on delete cascade,
  user_id uuid,
  cohort text not null default 'beta',
  locale text,

  -- stage 1: pre-result pulse (loading screen, non-blocking)
  s1_clarity smallint,
  s1_feeling smallint,
  s1_understood smallint,
  stage1_completed_at timestamptz,

  -- stage 2: post-result full form
  language_used text,
  understood_after smallint,
  personality_accuracy text,
  values_accuracy text,
  strengths_accuracy text,
  career_matches_accuracy text,
  wrong_career_text text,
  missing_career_text text,
  ai_impact_useful smallint,
  ai_impact_credible smallint,
  ai_impact_changed_thinking text,
  jobs_relevant smallint,
  companies_fit smallint,
  courses_useful smallint,
  plan_would_follow text,
  clear_next_step text,
  arabic_natural text,
  overall_value smallint,
  most_valuable_parts text[],
  would_pay text,
  would_recommend text,
  device text,
  had_issues text,
  issue_detail text,
  surprised_text text,
  not_me_text text,
  other_text text,
  stage2_completed_at timestamptz,

  created_at timestamptz not null default now()
);

create unique index if not exists beta_feedback_response_id_key on beta_feedback(response_id);
