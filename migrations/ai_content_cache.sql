alter table assessment_responses add column if not exists ai_content_cache jsonb;
alter table assessment_responses add column if not exists ai_impact_cache_ar jsonb;
alter table assessment_responses add column if not exists ai_content_cache_ar jsonb;
