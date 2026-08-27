create table if not exists app_settings (
  key text primary key,
  value jsonb,
  updated_at timestamptz default now()
);

insert into app_settings (key, value) values
('smtp_settings', '{}'::jsonb)
on conflict (key) do nothing;
