-- Captures whether the user's field of study was actually their own choice,
-- plus why not when it wasn't — relevant especially for Saudi users, where
-- university placement is often assigned rather than freely chosen.
ALTER TABLE assessment_responses
  ADD COLUMN IF NOT EXISTS major_was_own_choice text,
  ADD COLUMN IF NOT EXISTS major_choice_reason text;

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
    sectors_of_interest, career_structure,
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
