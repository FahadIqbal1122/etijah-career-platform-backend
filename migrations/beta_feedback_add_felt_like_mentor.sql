-- "Did it feel like a mentor who understands your context, or a generic quiz?"
-- Measures perceived personalization/tone, distinct from understood_after
-- (accuracy of understanding) — a report can be accurate but still read as
-- generic, or feel personal even where it got a detail wrong.
alter table beta_feedback add column if not exists felt_like_mentor text;
