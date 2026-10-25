-- The buyer's IP / user agent / Meta cookies, saved at checkout so the payment webhook (server-to-server)
-- can send them with the Meta Purchase event. Read and written by the backend with the service role.
create table if not exists public.checkout_context (
  user_id uuid primary key,
  client_ip text,
  client_user_agent text,
  fbp text,
  fbc text,
  updated_at timestamptz not null default now()
);
alter table public.checkout_context enable row level security;
