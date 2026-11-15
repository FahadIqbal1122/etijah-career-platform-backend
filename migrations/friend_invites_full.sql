-- Friend comparison, phase 2 (after payment): each person agrees a second time before the fuller comparison
-- (shared careers, who leads, where they complement each other) opens. Run after friend_invites.sql.
alter table friend_invites add column if not exists inviter_full_consent_at timestamptz;
alter table friend_invites add column if not exists friend_full_consent_at timestamptz;
