-- Share-with-parent payment links for under-18 buyers: the child creates a link, a parent opens it (no login) and pays
-- for the child's account. The row is closed (paid_at) by the payment webhook.
create table if not exists parent_payment_links (
  token text primary key,
  user_id uuid not null,
  plan_code text not null,
  currency text,
  locale text default 'en',
  created_at timestamptz default now(),
  expires_at timestamptz not null,
  paid_at timestamptz
);
create index if not exists parent_payment_links_user_idx on parent_payment_links (user_id);
alter table parent_payment_links enable row level security;  -- the backend uses the service key; no public policies
