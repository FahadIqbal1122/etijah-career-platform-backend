-- ============================================================
-- Organization (email-domain) free report seats  -- run once in the Supabase SQL editor
-- Safe to re-run, and safe on top of the first version of this file (it upgrades the old tables in place).
-- ============================================================

create table if not exists org_domains (
  id          uuid primary key default gen_random_uuid(),
  domain      text unique not null
              check (domain = lower(domain) and domain ~ '^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$'),
  org_name    text,
  plan_code   text not null default 'pathfinder'
              check (plan_code in ('pathfinder', 'launchpad_monthly')),
  seat_limit  int  not null check (seat_limit > 0),
  expires_at  timestamptz,                 -- null = no end date
  active      boolean not null default true,
  created_at  timestamptz not null default now()
);

create table if not exists org_domain_grants (
  domain_id   uuid not null references org_domains(id) on delete cascade,
  user_id     uuid not null,
  email       text not null,
  -- the part before the @ with any "+tag" removed: name+1@ and name+2@ are the same mailbox, so they share one seat
  email_key   text not null,
  granted_at  timestamptz not null default now(),
  revoked_at  timestamptz,                 -- set when an admin takes the seat back; the person cannot re-claim it
  primary key (domain_id, user_id),
  unique (domain_id, email_key)
);

create index if not exists org_domain_grants_user_idx on org_domain_grants (user_id);

-- ---- Bring an earlier version of these tables up to date (does nothing on a fresh setup; keeps existing data) ----
alter table org_domain_grants add column if not exists revoked_at timestamptz;
alter table org_domain_grants add column if not exists email_key text;
update org_domain_grants
   set email_key = regexp_replace(split_part(lower(email), '@', 1), '\+.*$', '')
 where email_key is null;
alter table org_domain_grants alter column email_key set not null;
do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'org_domain_grants_domain_id_email_key_key') then
    alter table org_domain_grants add constraint org_domain_grants_domain_id_email_key_key unique (domain_id, email_key);
  end if;
end $$;
alter table org_domains drop constraint if exists org_domains_domain_check;
alter table org_domains add constraint org_domains_domain_check
  check (domain = lower(domain) and domain ~ '^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$');

-- Backend uses the service key. RLS on with no policies, and no direct privileges for the browser roles.
alter table org_domains       enable row level security;
alter table org_domain_grants enable row level security;
revoke all on org_domains, org_domain_grants from public, anon, authenticated;

-- Atomic seat claim: the row lock serialises concurrent claims per domain, so the limit can never be overshot.
-- Returns granted | already | revoked | duplicate | full | no_offer.
create or replace function claim_org_seat(p_domain text, p_user_id uuid, p_email text)
returns table (status text, plan_code text, org_name text)
language plpgsql
security definer
set search_path = public
as $$
declare
  d org_domains%rowtype;
  g org_domain_grants%rowtype;
  used int;
  k text := regexp_replace(split_part(lower(p_email), '@', 1), '\+.*$', '');
begin
  select * into d from org_domains where domain = lower(p_domain) for update;

  if not found or not d.active or (d.expires_at is not null and d.expires_at <= now()) then
    return query select 'no_offer'::text, null::text, null::text;
    return;
  end if;

  select * into g from org_domain_grants x where x.domain_id = d.id and x.user_id = p_user_id;
  if found then
    return query select (case when g.revoked_at is null then 'already' else 'revoked' end)::text, d.plan_code, d.org_name;
    return;
  end if;

  -- same mailbox under another alias (or a revoked person's alias): no second seat
  if exists (select 1 from org_domain_grants x where x.domain_id = d.id and x.email_key = k) then
    return query select 'duplicate'::text, d.plan_code, d.org_name;
    return;
  end if;

  select count(*) into used from org_domain_grants x where x.domain_id = d.id and x.revoked_at is null;
  if used >= d.seat_limit then
    return query select 'full'::text, d.plan_code, d.org_name;
    return;
  end if;

  insert into org_domain_grants (domain_id, user_id, email, email_key)
  values (d.id, p_user_id, lower(p_email), k);

  return query select 'granted'::text, d.plan_code, d.org_name;
end;
$$;

revoke all on function claim_org_seat(text, uuid, text) from public, anon, authenticated;
grant execute on function claim_org_seat(text, uuid, text) to service_role;

-- Admin overview: seats in use per domain (revoked seats are free again)
create or replace view org_domain_usage with (security_invoker = true) as
select d.*, count(g.user_id) filter (where g.revoked_at is null)::int as seats_used
from org_domains d
left join org_domain_grants g on g.domain_id = d.id
group by d.id;

revoke all on org_domain_usage from public, anon, authenticated;
grant select on org_domain_usage to service_role;

-- Starting offer (more can be added from Admin > Settings > Organization Access)
insert into org_domains (domain, org_name, plan_code, seat_limit) values
  ('etijahcoaching.com', 'Etijah Coaching', 'pathfinder', 5)
on conflict (domain) do nothing;
