-- Captures whether the user wants to stay in their current field, move into
-- something different, or isn't sure yet — feeds the field-overlap weighting
-- in scoring_engine.py's score_careers() (a familiar-field match is not
-- automatically a good match if the person wants out of that field).
--
-- Also re-fixes a regression: fix_insert_assessment_response_education_field_array.sql
-- (filename-sorts after add_major_was_own_choice.sql, so it runs later on a
-- from-scratch bootstrap that applies migrations/*.sql in filename order) had
-- its own INSERT column list drop major_was_own_choice/major_choice_reason,
-- silently reverting them to NULL on every future submission. This migration
-- restores the full, current column list so it can't happen again.
ALTER TABLE assessment_responses
  ADD COLUMN IF NOT EXISTS career_direction text;

CREATE OR REPLACE FUNCTION public.insert_assessment_response(payload jsonb)
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
  result_id uuid;
BEGIN
  INSERT INTO assessment_responses (
    full_name, email, phone, country, nationality, age, experience_level,
    current_stage, education_field, major_was_own_choice, major_choice_reason,
    career_direction, sectors_of_interest, career_structure,
    languages, geographic_openness, why_here, answers, completed, locale
  ) VALUES (
    payload->>'full_name',
    payload->>'email',
    payload->>'phone',
    payload->>'country',
    payload->>'nationality',
    (payload->>'age')::integer,
    payload->>'experience_level',
    payload->>'current_stage',
    ARRAY(SELECT jsonb_array_elements_text(payload->'education_field')),
    payload->>'major_was_own_choice',
    payload->>'major_choice_reason',
    payload->>'career_direction',
    ARRAY(SELECT jsonb_array_elements_text(payload->'sectors_of_interest')),
    payload->>'career_structure',
    ARRAY(SELECT jsonb_array_elements_text(payload->'languages')),
    payload->>'geographic_openness',
    payload->>'why_here',
    payload->'answers',
    (payload->>'completed')::boolean,
    coalesce(payload->>'locale', 'en')
  )
  RETURNING id INTO result_id;

  RETURN result_id;
END;
$function$
