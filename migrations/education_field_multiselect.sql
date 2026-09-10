-- QO5 (university field) became multi-select — the user can now pick up to
-- 2 fields (e.g. "Business" + "Computer Science") instead of one. Widen the
-- column from text to text[] to match sectors_of_interest/languages, wrapping
-- any existing single value into a one-element array (empty/null -> '{}').
alter table assessment_responses
  alter column education_field type text[]
  using case
    when education_field is null or education_field = '' then '{}'::text[]
    else array[education_field]
  end;
