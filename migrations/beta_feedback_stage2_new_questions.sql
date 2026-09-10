-- Noora's new/revised Stage 2 questions: how many suggested careers they'd
-- seriously consider, a reason when they wouldn't pay, interest in a coach
-- session, and (once per-career explanations exist) whether they understood
-- each suggested career.
alter table beta_feedback
  add column if not exists careers_seriously_considered text,
  add column if not exists would_pay_reason text,
  add column if not exists wants_coach_session text,
  add column if not exists career_understanding_text text;
