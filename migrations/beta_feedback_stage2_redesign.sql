-- Stage 2 redesign per the 10 Sept beta-strategy doc: collapses ~30 fields
-- down to ~12 questions (see BetaFeedbackStage2Request / stage2Sections).
-- Old columns are left in place (harmless, still hold historical Beta 1
-- answers for personality_accuracy/values_accuracy/etc, ai_impact_credible,
-- surprised_text, not_me_text, would_pay_reason, most_valuable_parts, ...) —
-- this migration only adds the new columns the redesigned form now writes.
alter table beta_feedback
  add column if not exists career_explained text,
  add column if not exists most_useful_part text,
  add column if not exists least_useful_part text,
  add column if not exists first_action_text text,
  add column if not exists would_pay_at_price text,
  add column if not exists pay_blockers text[],
  add column if not exists pay_blocker_other_text text,
  add column if not exists pay_blocker_priority text,
  add column if not exists worth_paying_for text[];
