-- ============================================================================
-- Local Development Schema (Auth + Tracking)
-- This file defines local-only tables for user authentication and agent run
-- tracking. It is designed to be easily migrated to Supabase later.
--
-- IMPORTANT: In production with Supabase, the `public.users` table here will be
-- replaced by `auth.users` (managed by Supabase Auth). Foreign keys should then
-- be adjusted accordingly (profiles.user_id -> auth.users.id, etc).
--
-- Apply this schema AFTER the core Agno/agent-api has created its own tables.
-- You can execute it manually (psql) or integrate with a simple migration step.
--
-- psql example:
--   psql 'postgresql://ai:ai@localhost:5432/ai?sslmode=disable' -f db/schema_local.sql
--
-- ============================================================================

-- ============================================================================
-- Extensions (idempotent)
-- ============================================================================
create extension if not exists pgcrypto;
create extension if not exists "uuid-ossp";
create extension if not exists citext;

-- ============================================================================
-- 1) Local Users Table
--    In Supabase production this will be replaced by auth.users.
--    Columns chosen to ease migration.
-- ============================================================================
create table if not exists public.users (
  id uuid primary key default gen_random_uuid(),
  email citext unique not null,
  password_hash text not null,              -- Argon2 / bcrypt hash (never store plaintext)
  created_at timestamptz default now(),
  last_login_at timestamptz
);

comment on table public.users is 'Local-only user auth table. Replace with auth.users when migrating to Supabase.';
comment on column public.users.email is 'User email (citext for case-insensitive uniqueness).';
comment on column public.users.password_hash is 'Hashed password using bcrypt/argon2.';
comment on column public.users.last_login_at is 'Timestamp of last successful login.';

-- Fast lookup by email
create index if not exists idx_users_email on public.users(email);

-- ============================================================================
-- 2) Profiles
--    Survives migration. When moving to Supabase, change FK to auth.users(id).
-- ============================================================================
create table if not exists public.profiles (
  user_id uuid primary key references public.users(id) on delete cascade,
  display_name text,
  avatar_url text,
  created_at timestamptz default now()
);

comment on table public.profiles is 'User profile metadata separate from auth core.';
comment on column public.profiles.display_name is 'Human-friendly display name.';
comment on column public.profiles.avatar_url is 'URL to avatar image.';

-- ============================================================================
-- 3) Agent Runs
--    Higher-level tracking around the animation or chat pipelines.
--    Supplements Agno internal session tables (e.g. animation_agent_sessions).
-- ============================================================================
create table if not exists public.agent_runs (
  run_id uuid primary key,                         -- Externally generated UUID (align with pipeline run_id)
  user_id uuid references public.users(id) on delete set null,
  session_id text,                                 -- Links to Agno session if applicable
  agent_id text not null,                          -- e.g. 'animation_agent'
  state text not null,                             -- STARTING | PREVIEWING | RENDERING | COMPLETED | FAILED | EXPORTING
  message text,                                    -- Original user prompt
  metadata jsonb default '{}'::jsonb,              -- Arbitrary extra data (chart spec, overrides, etc.)
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

comment on table public.agent_runs is 'Tracks lifecycle of agent executions alongside internal session tables.';
comment on column public.agent_runs.metadata is 'JSON blob for auxiliary config/state.';

create index if not exists idx_agent_runs_user_id on public.agent_runs(user_id);
create index if not exists idx_agent_runs_created_at on public.agent_runs(created_at);
create index if not exists idx_agent_runs_state on public.agent_runs(state);

-- Simple trigger to auto-update updated_at
create or replace function public.touch_agent_runs_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_touch_agent_runs_updated_at on public.agent_runs;
create trigger trg_touch_agent_runs_updated_at
before update on public.agent_runs
for each row execute procedure public.touch_agent_runs_updated_at();

-- ============================================================================
-- 4) Datasets
--    Metadata for user-uploaded CSV or other data sources.
--    Local: storage_path points to artifacts/datasets/<uuid>.csv
--    Future Supabase: storage_path becomes a public/signed URL in a storage bucket.
-- ============================================================================
create table if not exists public.datasets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.users(id) on delete set null,
  filename text not null,
  storage_path text not null,                -- Local path or remote URL
  size_bytes bigint,
  mime_type text,
  checksum text,                             -- Optional SHA256 or similar
  created_at timestamptz default now()
);

comment on table public.datasets is 'User-uploaded datasets referenced in animation/code generation.';
comment on column public.datasets.storage_path is 'Local filesystem path or cloud storage URL.';
comment on column public.datasets.checksum is 'Hash for integrity verification.';

create index if not exists idx_datasets_user_id on public.datasets(user_id);
create index if not exists idx_datasets_created_at on public.datasets(created_at);
create index if not exists idx_datasets_filename on public.datasets(filename);

-- ============================================================================
-- 5) Artifacts
--    Output products (preview frames, final videos, logs, compressed bundles).
--    Linked to agent_runs for rollup coordination.
-- ============================================================================
create table if not exists public.artifacts (
  id uuid primary key default gen_random_uuid(),
  run_id uuid references public.agent_runs(run_id) on delete cascade,
  kind text not null,                        -- preview_frame | preview_zip | video | log | other
  storage_path text not null,                -- Local path or remote URL
  width int,
  height int,
  duration_ms int,
  created_at timestamptz default now()
);

comment on table public.artifacts is 'Generated media/output tied to a specific agent run.';
comment on column public.artifacts.kind is 'Type classification of the artifact.';
comment on column public.artifacts.storage_path is 'Location of artifact (file path or URL).';

create index if not exists idx_artifacts_run_id on public.artifacts(run_id);
create index if not exists idx_artifacts_kind on public.artifacts(kind);
create index if not exists idx_artifacts_created_at on public.artifacts(created_at);

-- ============================================================================
-- 6) Future RLS (When Migrating to Supabase)
--    For local dev we usually do not enable RLS. When moving to Supabase:
--      alter table ... enable row level security;
--      create policy ... using (auth.uid() = user_id);
--    Skip for local to keep complexity minimal.
-- ============================================================================

-- ============================================================================
-- 7) Convenience Views (Optional)
--    Example: join runs + artifacts count
-- ============================================================================
create or replace view public.v_agent_run_summary as
select
  r.run_id,
  r.user_id,
  r.agent_id,
  r.state,
  r.created_at,
  r.updated_at,
  (select count(*) from public.artifacts a where a.run_id = r.run_id) as artifact_count
from public.agent_runs r;

comment on view public.v_agent_run_summary is 'Summarized view of runs with artifact count.';

-- ============================================================================
-- 8) Sanity Checks
-- ============================================================================
-- select 'users' as table, count(*) as rows from public.users;
-- select 'profiles' as table, count(*) as rows from public.profiles;
-- select 'agent_runs' as table, count(*) as rows from public.agent_runs;
-- select 'datasets' as table, count(*) as rows from public.datasets;
-- select 'artifacts' as table, count(*) as rows from public.artifacts;

-- ============================================================================
-- 9) Chat Sessions & Messages (Local Persistence)
--    These tables store conversational history per user.
--    In Supabase migration:
--      - Change user_id FK to auth.users(id)
--      - Optionally enable RLS policies.
-- ============================================================================
create table if not exists public.chat_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.users(id) on delete cascade,
  name text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

comment on table public.chat_sessions is 'Logical chat/conversation container per user.';
comment on column public.chat_sessions.name is 'Optional human-friendly session name.';

-- Auto-update updated_at on change
create or replace function public.touch_chat_sessions_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_touch_chat_sessions_updated_at on public.chat_sessions;
create trigger trg_touch_chat_sessions_updated_at
before update on public.chat_sessions
for each row execute procedure public.touch_chat_sessions_updated_at();

create index if not exists idx_chat_sessions_user_id on public.chat_sessions(user_id);
create index if not exists idx_chat_sessions_created_at on public.chat_sessions(created_at);

-- ============================================================================
-- Chat Messages
-- role constraint keeps data consistent. extra_json can store tool calls,
-- reasoning steps, references, etc.
-- ============================================================================
create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references public.chat_sessions(id) on delete cascade,
  user_id uuid references public.users(id) on delete set null,
  role text not null check (role in ('user','agent','system','tool')),
  content text not null,
  extra_json jsonb,
  created_at timestamptz default now()
);

comment on table public.chat_messages is 'Individual messages within a chat session.';
comment on column public.chat_messages.role is 'Origin of message: user | agent | system | tool.';
comment on column public.chat_messages.extra_json is 'Optional structured metadata (tool calls, reasoning, etc).';

create index if not exists idx_chat_messages_session_created on public.chat_messages(session_id, created_at);
create index if not exists idx_chat_messages_user_id on public.chat_messages(user_id);

-- End of schema_local.sql
