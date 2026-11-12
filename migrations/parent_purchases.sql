-- Parent-pays-first: a parent buys the report for their child BEFORE the child has an account.
-- token        = the child's gift link (shared by the parent with the child)
-- parent_token = the parent's private status page (also the link in their emails)
-- holder_user_id = the auth user the shop order is booked under (the parent's own account, created silently if needed);
--                  the plan is NOT activated on it, it is activated on the child's account when the child redeems.
create table if not exists parent_purchases (
  token text primary key,
  parent_token text unique not null,
  parent_email text not null,
  child_first_name text,
  plan_code text not null,
  currency text,
  locale text default 'en',
  holder_user_id uuid not null,
  order_ref text unique,
  parent_consent_at timestamptz,
  child_consent_at timestamptz,
  created_at timestamptz default now(),
  paid_at timestamptz,
  redeemed_by uuid,
  redeemed_at timestamptz
);
create index if not exists parent_purchases_holder_idx on parent_purchases (holder_user_id);
alter table parent_purchases enable row level security;  -- the backend uses the service key; no public policies
