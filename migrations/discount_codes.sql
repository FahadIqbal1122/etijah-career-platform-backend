create table if not exists discount_codes (
  id uuid primary key default gen_random_uuid(),
  code text not null,
  description text,
  discount_type text not null check (discount_type in ('percent','fixed')),
  percent_off numeric(5,2),
  fixed_off_sar numeric(10,2),
  plan_codes text[],                                  -- null = every plan
  max_redemptions int check (max_redemptions is null or max_redemptions >= 1),   -- null = unlimited
  max_per_user int not null default 1 check (max_per_user >= 1),
  starts_at timestamptz,
  expires_at timestamptz,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint discount_code_format check (code ~ '^[A-Z0-9_-]{3,32}$'),
  constraint discount_value check (
    (discount_type = 'percent' and percent_off is not null and percent_off > 0 and percent_off <= 95 and fixed_off_sar is null) or
    (discount_type = 'fixed'   and fixed_off_sar is not null and fixed_off_sar > 0 and percent_off is null)),
  constraint discount_window check (starts_at is null or expires_at is null or starts_at < expires_at)
);
create unique index if not exists discount_codes_code_uq on discount_codes (code);

create table if not exists discount_redemptions (
  id uuid primary key default gen_random_uuid(),
  code_id uuid not null references discount_codes(id) on delete restrict,
  user_id uuid not null,
  email text,
  plan_code text not null,
  order_ref text unique,                 -- the Shop's order reference, filled in once the order exists
  currency text,
  original_amount numeric(12,3),
  discount_amount numeric(12,3),
  final_amount numeric(12,3),
  status text not null default 'reserved' check (status in ('reserved','redeemed','released')),
  created_at timestamptz not null default now(),
  redeemed_at timestamptz
);
create index if not exists discount_redemptions_code_idx on discount_redemptions (code_id, status, created_at);
create index if not exists discount_redemptions_user_idx on discount_redemptions (user_id, code_id);

-- Backend (service role) only: no policies, so the browser can never read or write these tables.
alter table discount_codes enable row level security;
alter table discount_redemptions enable row level security;

create or replace view discount_code_usage with (security_invoker = true) as
select c.*,
  count(r.id) filter (where r.status = 'redeemed') as redeemed_count,
  count(r.id) filter (where r.status = 'reserved' and r.created_at > now() - interval '45 minutes') as pending_count
from discount_codes c left join discount_redemptions r on r.code_id = c.id
group by c.id;

-- One locked step: check the code and take a use (p_dry_run = check only, used for the price preview).
create or replace function reserve_discount_code(
  p_code text, p_user_id uuid, p_email text, p_plan_code text,
  p_dry_run boolean default false, p_hold_minutes int default 45)
returns jsonb language plpgsql security definer set search_path = public as $$
declare c discount_codes%rowtype; v_used int; v_mine int; v_id uuid;
begin
  select * into c from discount_codes where code = upper(trim(p_code)) for update;   -- row lock = no race on the last use
  if not found or not c.active then return jsonb_build_object('ok', false, 'error', 'invalid'); end if;
  if c.starts_at is not null and now() < c.starts_at then return jsonb_build_object('ok', false, 'error', 'not_started'); end if;
  if c.expires_at is not null and now() >= c.expires_at then return jsonb_build_object('ok', false, 'error', 'expired'); end if;
  if c.plan_codes is not null and not (p_plan_code = any(c.plan_codes)) then return jsonb_build_object('ok', false, 'error', 'wrong_plan'); end if;

  if not p_dry_run then   -- a retry never blocks itself: drop this buyer's own unfinished attempts first
    update discount_redemptions set status = 'released'
      where code_id = c.id and user_id = p_user_id and status = 'reserved';
  end if;

  select count(*) into v_mine from discount_redemptions
    where code_id = c.id and user_id = p_user_id
      and (status = 'redeemed' or (status = 'reserved' and created_at > now() - make_interval(mins => p_hold_minutes)));
  if v_mine >= c.max_per_user then return jsonb_build_object('ok', false, 'error', 'already_used'); end if;

  if c.max_redemptions is not null then
    select count(*) into v_used from discount_redemptions
      where code_id = c.id
        and (status = 'redeemed' or (status = 'reserved' and created_at > now() - make_interval(mins => p_hold_minutes)));
    if v_used >= c.max_redemptions then return jsonb_build_object('ok', false, 'error', 'used_up'); end if;
  end if;

  if not p_dry_run then
    insert into discount_redemptions (code_id, user_id, email, plan_code)
      values (c.id, p_user_id, p_email, p_plan_code) returning id into v_id;
  end if;
  return jsonb_build_object('ok', true, 'redemption_id', v_id, 'code_id', c.id,
    'discount_type', c.discount_type, 'percent_off', c.percent_off, 'fixed_off_sar', c.fixed_off_sar);
end $$;
revoke all on function reserve_discount_code(text, uuid, text, text, boolean, int) from public, anon, authenticated;
grant execute on function reserve_discount_code(text, uuid, text, text, boolean, int) to service_role;
