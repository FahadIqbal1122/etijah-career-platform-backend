create table if not exists partner_inquiries (
  id uuid primary key default gen_random_uuid(),
  company_name text not null,
  contact_name text not null,
  email text not null,
  phone text,
  message text,
  locale text,
  source text,
  created_at timestamptz default now()
);

create index if not exists partner_inquiries_created_at_idx on partner_inquiries (created_at);
