-- vector store creation

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
  id UUID PRIMARY KEY,
  content TEXT,
  metadata JSONB,
  embedding VECTOR(384)  -- Use the correct dimension for your embedding model
);


CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

--RPC

CREATE OR REPLACE FUNCTION public.diet_weekly(uid text)
RETURNS TABLE (
    week int,
    avg_protein numeric,
    avg_carbs numeric,
    avg_veggies numeric,
    junk_food_days int
) AS $$
    SELECT
        ((EXTRACT(DOY FROM date) - EXTRACT(DOY FROM DATE '2025-08-01'  - interval '30 days')) / 7 + 1)::int AS week,
        ROUND(AVG(protein_serving),2) AS avg_protein,
        ROUND(AVG(carb_serving),2) AS avg_carbs,
        ROUND(AVG(vegetable_serving),2) AS avg_veggies,
        SUM(CASE WHEN carb_serving > 70 THEN 1 ELSE 0 END) AS junk_food_days
    FROM diets
    WHERE user_id = uid
      AND date >= DATE '2025-08-01' - interval '30 days'
    GROUP BY week
    ORDER BY week;
$$ LANGUAGE sql STABLE;


CREATE OR REPLACE FUNCTION public.exercise_weekly(uid text)
RETURNS TABLE (
    week int,
    activity text,
    avg_duration numeric,
    sessions int
) AS $$
    SELECT
        ((EXTRACT(DOY FROM date) - EXTRACT(DOY FROM DATE '2025-08-01' - interval '30 days')) / 7 + 1)::int AS week,
        activity,
        ROUND(AVG(duration_minutes), 2) AS avg_duration,
        COUNT(*) AS sessions
    FROM exercises
    WHERE user_id = uid
      AND date >= DATE '2025-08-01' - interval '30 days'
    GROUP BY week, activity
    ORDER BY week, activity;
$$ LANGUAGE sql STABLE;


----



CREATE OR REPLACE FUNCTION public.profile_info(uid text)
RETURNS TABLE (
    name text,
    age int,
    sex text,
    bmi numeric,
    bmi_category text,
    diabetes_type text
) AS $$
    SELECT
    name,
    age,
    sex,
    bmi,
    CASE
        WHEN bmi < 18.5 THEN 'Underweight'
        WHEN bmi >= 18.5 AND bmi < 25 THEN 'Normal weight'
        WHEN bmi >= 25 AND bmi < 30 THEN 'Overweight'
        WHEN bmi >= 30 AND bmi < 35 THEN 'Obesity class I'
        WHEN bmi >= 35 AND bmi < 40 THEN 'Obesity class II'
        ELSE 'Obesity class III'
    END AS bmi_category,
    diabetes_type
FROM profiles
WHERE user_id = uid;
$$ LANGUAGE sql STABLE;


CREATE OR REPLACE FUNCTION public.weekly_habits(uid text)
RETURNS TABLE (
    week int,
    avg_drinks numeric,
    avg_cigarettes numeric
) AS $$
SELECT
    ((EXTRACT(DOY FROM a.date) - EXTRACT(DOY FROM DATE '2025-08-01' - INTERVAL '30 days')) / 7 + 1)::int AS week,
    ROUND(AVG(drinks), 2) AS avg_drinks,
    ROUND(AVG(cigarettes_per_day), 2) AS avg_cigarettes
FROM alcohol a
JOIN smoking s
    ON a.user_id = s.user_id
    AND a.date = s.date
WHERE a.user_id = uid
  AND a.date >= DATE '2025-08-01' - INTERVAL '30 days'
GROUP BY week
ORDER BY week;
$$ LANGUAGE sql STABLE;


CREATE OR REPLACE FUNCTION public.mental_health_status(uid text)
RETURNS TABLE (
    mental_health_issue text
) AS $$
    SELECT
    last_recorded_issue
FROM mental_health
WHERE user_id = uid;
$$ LANGUAGE sql STABLE;


CREATE OR REPLACE FUNCTION public.weekly_medications(uid TEXT)
RETURNS TABLE (
    week INT,
    type TEXT,
    medication_name TEXT,
    unit_type TEXT,
    avg_dosage NUMERIC
)
AS $$
    SELECT
        (
            (EXTRACT(doy FROM date) - EXTRACT(doy FROM DATE '2025-08-01' - INTERVAL '30 days'))
            / 7 + 1
        )::int AS week,
        type,
        medication_name,
        unit_type,
        ROUND(AVG(dosage), 2) AS avg_dosage
    FROM
        medications
    WHERE
        user_id = uid
        AND date >= DATE '2025-08-01' - INTERVAL '30 days'
    GROUP BY
        week, type, medication_name, unit_type
    ORDER BY
        week;
$$ LANGUAGE sql STABLE;

---
CREATE OR REPLACE FUNCTION public.weekly_water_intake(uid TEXT)
RETURNS TABLE (
    week INT,
    avg_target_intake_ml NUMERIC,
    avg_actual_intake_ml NUMERIC,
    avg_num_glasses NUMERIC,
    avg_hydration_score NUMERIC
)
AS $$
    SELECT
        (
            (EXTRACT(doy FROM date) - EXTRACT(doy FROM DATE '2025-08-01' - INTERVAL '30 days'))
            / 7 + 1
        )::int AS week,
        ROUND(AVG(target_intake_ml), 2) AS avg_target_intake_ml,
        ROUND(AVG(actual_intake_ml), 2) AS avg_actual_intake_ml,
        ROUND(AVG(num_glasses), 2) AS avg_num_glasses,
        ROUND(AVG(hydration_score)::numeric, 2) AS avg_hydration_score
    FROM
        water_intake
    WHERE
        user_id = uid
        AND date >= DATE '2025-08-01' - INTERVAL '30 days'
    GROUP BY
        week
    ORDER BY
        week;
$$ LANGUAGE sql STABLE;

----

create or replace function public.dashboard_weekly_all_v1(uid text)
returns jsonb
language sql
security invoker
set search_path = public
as $$
select jsonb_build_object(
  'diet',           coalesce((select jsonb_agg(to_jsonb(d) order by d.week)
                              from public.diet_weekly(uid) d), '[]'::jsonb),
  'exercise',       coalesce((select jsonb_agg(to_jsonb(x) order by x.week, x.activity)
                              from public.exercise_weekly(uid) x), '[]'::jsonb),
  'habits',         coalesce((select jsonb_agg(to_jsonb(h) order by h.week)
                              from public.weekly_habits(uid) h), '[]'::jsonb),
  'medications',    coalesce((select jsonb_agg(to_jsonb(m) order by m.week, m.type, m.medication_name)
                              from public.weekly_medications(uid) m), '[]'::jsonb),
  'profile_info',   coalesce((select to_jsonb(p)
                              from public.profile_info(uid) p
                              limit 1), '{}'::jsonb),
  'mental_health',  coalesce((select jsonb_agg(to_jsonb(s))
                              from public.mental_health_status(uid) s), '[]'::jsonb),
   'water_intake',  coalesce((select jsonb_agg(to_jsonb(s))
                              from public.mental_health_status(uid) s), '[]'::jsonb)
);
$$;


-- Latest medical KPIs for a user (wide schema)
create or replace function public.medical_tests_latest(uid text)
returns table (
  recorded_at date,
  fasting_glucose numeric,
  hba1c numeric,
  ldl numeric,
  hdl numeric,
  systolic_bp int,
  diastolic_bp int
)
language sql
stable
as $$
  select
    test_date as recorded_at,
    fasting_glucose,
    hba1c,
    ldl,
    hdl,
    systolic_bp,
    diastolic_bp
  from medical_tests
  where user_id = uid
  order by test_date desc
  limit 1;
$$;

-- (Recommended) index for fast lookup
create index if not exists medical_tests_user_date_idx
  on medical_tests (user_id, test_date desc);


-- Latest medical KPIs for a user (wide schema)
create or replace function public.profile_details(uid text)
returns table (
  name text,
  age int,
  sex text,
  bmi float,
  diabetes_type text
)
language sql
stable
as $$
  select
    name,
    age,
    sex,
    bmi,
    diabetes_type
  from profiles
  where user_id = uid
  limit 1;
$$;

-- (Recommended) index for fast lookup
create index if not exists profile_details_idx
  on medical_tests (user_id, test_date desc);


create or replace function schema_snapshot_v1(tables text[])
returns setof jsonb
language sql
stable
as $$
  with cols as (
    select
      table_name,
      column_name,
      data_type,
      ordinal_position
    from information_schema.columns
    where table_schema = 'public'
      and table_name = any(tables)
    order by table_name, ordinal_position
  )
  select jsonb_build_object(
           'table', table_name,
           'columns', jsonb_agg(
               jsonb_build_object('name', column_name, 'type', data_type)
               order by ordinal_position
           )
         )
  from cols
  group by table_name
  order by table_name;
$$;

grant execute on function schema_snapshot_v1(text[]) to anon, authenticated;

create or replace function exec_sql_readonly_v2(query text)
returns setof jsonb
language plpgsql
security invoker
set search_path = public
as $$
declare
  clean text;
begin
  -- Strip BOM
  clean := regexp_replace(query, E'^\uFEFF', '', 'g');

  -- Remove leading code fences/backticks if any (defensive)
  clean := regexp_replace(clean, E'^\\s*```(?:sql)?\\s*', '', 'i');
  clean := regexp_replace(clean, E'\\s*```\\s*$', '', 'g');

  -- Remove leading SQL comments and whitespace
  clean := regexp_replace(clean, E'^\\s*(?:--[^\\n]*\\n|/\\*.*?\\*/\\s*)*', '', 'gs');

  -- Strip trailing semicolons
  clean := regexp_replace(clean, E';\\s*$', '', 'g');

  /* if clean !~* '^(select|with)\\b' then
    raise exception 'Only SELECT/WITH allowed';
  end if; */

  perform set_config('statement_timeout','3000', true);
  return query execute format('select to_jsonb(q) from (%s limit 500) q', clean);
end;
$$;



grant execute on function exec_sql_readonly_v2(query text) to anon, authenticated;