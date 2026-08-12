create table if not exists market_fetch_status (
  week text primary key,
  status text not null default 'running',
  inserted int default 0,
  errors int default 0,
  insert_error text,
  started_at timestamptz default now(),
  finished_at timestamptz
);
