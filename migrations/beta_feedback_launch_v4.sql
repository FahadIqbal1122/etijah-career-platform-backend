-- Launch feedback questions (7 Oct 2026 doc): 4 loading-screen questions, 4 results-page
-- questions, then a free (7+2) or paid (12) follow-up. Additive only: every beta column stays.
-- Reused columns: s1_understood (Q1), s1_intent (Q2), result_accuracy (Q5), career_explained (Q6),
-- careers_seriously_considered (Q7), other_text (Q8), felt_like_mentor (Q9), most_useful_part (Q10),
-- ai_impact_changed_thinking (Q11), wants_coach_session (Q13), would_recommend (Q14),
-- arabic_natural (Q15), pay_blocker_other_text (Q17), overall_value (Q18), jobs_relevant (Q19),
-- courses_useful (Q20), plan_would_follow (Q21), least_useful_part (Q22).
alter table beta_feedback
  add column if not exists plan_tier text check (plan_tier in ('free', 'paid')),
  add column if not exists form_version text,
  add column if not exists s1_confidence smallint check (s1_confidence between 1 and 5),  -- Q3
  add column if not exists s1_length text,                                                 -- Q4
  add column if not exists first_step text[],                                              -- Q12 (free)
  add column if not exists purchase_blocker text,                                          -- Q16 (free)
  add column if not exists missing_text text,                                              -- Q23 (paid)
  add column if not exists opened_ai_impact boolean not null default false;                -- gates Q11 for free users

-- Existing rows are the beta answers; everything inserted from now on is the launch form.
update beta_feedback set form_version = 'beta' where form_version is null;
alter table beta_feedback alter column form_version set default 'v4_launch';
