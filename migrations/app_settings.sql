create table if not exists app_settings (
  key text primary key,
  value jsonb,
  updated_at timestamptz default now()
);
