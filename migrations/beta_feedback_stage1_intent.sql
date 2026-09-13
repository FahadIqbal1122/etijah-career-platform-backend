-- Stage 1's new question per the 10 Sept beta-strategy doc: "What do you
-- most want from your results?" (confirm path / discover options / choose a
-- major / plan a change / get a job faster / understand AI impact).
-- Analytics-only for now — see BetaFeedbackStage1Request in main.py.
alter table beta_feedback
  add column if not exists s1_intent text;
