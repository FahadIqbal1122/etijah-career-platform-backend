-- education_field_multiselect.sql widened assessment_responses.education_field
-- from text to text[], but this RPC (called by POST /assessment/submit) still
-- extracted it with ->>'education_field' (text), so every submission started
-- failing with "column education_field is of type text[] but expression is
-- of type text". Cast it as an array the same way sectors_of_interest/
-- languages already are.
--
-- Superseded age_bracket (text) with age (integer) + experience_level (text)
-- when add_age_experience_level.sql landed — kept in sync here too since this
-- file sorts alphabetically after that one and would otherwise silently
-- revert the column list on a from-scratch DB bootstrap that applies
-- migrations/*.sql in filename order.
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
    current_stage, education_field, sectors_of_interest, career_structure,
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
