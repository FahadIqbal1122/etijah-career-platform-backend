-- Free results page ("snapshot"): the end-of-page quick questions no longer ask about suggested careers
-- (free users do not see any). Two new answers replace them for free users, form version 'v5_free_snapshot':
--   self_understanding: 'a_lot' | 'a_little' | 'not_really'   (Did this help you understand yourself better?)
--   unlock_intent:      'very_likely' | 'maybe' | 'not_likely' (How likely are you to unlock your career recommendations?)
-- Additive only: existing columns and rows are untouched.
alter table beta_feedback
  add column if not exists self_understanding text,
  add column if not exists unlock_intent text;
