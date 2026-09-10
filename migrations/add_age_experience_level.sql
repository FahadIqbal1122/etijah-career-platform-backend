-- Replaces the age_bracket onboarding question with an exact age plus a
-- separate experience-level question, so downstream logic (e.g. career/role
-- suggestions) can stop conflating age with seniority — a 23-year-old with
-- 5 years of work experience shouldn't be treated like a fresh grad.
--
-- age_bracket is left in place (untouched) rather than dropped, so existing
-- rows/reports that read it keep working; new submissions populate age +
-- experience_level instead and leave age_bracket null.
ALTER TABLE assessment_responses
  ADD COLUMN IF NOT EXISTS age integer,
  ADD COLUMN IF NOT EXISTS experience_level text;

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
