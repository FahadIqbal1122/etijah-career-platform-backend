-- Friend comparison (Noora's pay-gate point 15): a student at the pay gate invites a friend; the friend takes the free part;
-- both see a study-match teaser. Only the match percentage is ever shown to the other person.
-- token            = the invite link the inviter shares
-- inviter_name     = the inviter's first name, shown to the friend on the invite page (the inviter agreed to this)
-- friend_user_id   = set once, when the friend reaches the gate with an account and has agreed (friend_consent_at)
create table if not exists friend_invites (
  token text primary key,
  inviter_user_id uuid not null,
  inviter_name text,
  locale text default 'en',
  inviter_consent_at timestamptz not null,
  friend_user_id uuid,
  friend_consent_at timestamptz,
  created_at timestamptz default now()
);
create index if not exists friend_invites_inviter_idx on friend_invites (inviter_user_id);
create index if not exists friend_invites_friend_idx on friend_invites (friend_user_id);
alter table friend_invites enable row level security;  -- the backend uses the service key; no public policies
