alter table assessment_responses add column if not exists ai_impact_cache_free jsonb;
alter table assessment_responses add column if not exists ai_content_cache_free jsonb;
alter table assessment_responses add column if not exists ai_impact_cache_ar_free jsonb;
alter table assessment_responses add column if not exists ai_content_cache_ar_free jsonb;
