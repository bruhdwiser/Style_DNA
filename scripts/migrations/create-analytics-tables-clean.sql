-- FlashFit analytics and admin tables.
-- Run second in the Supabase SQL Editor, after scripts/schema.sql.
-- Safe to re-run: tables/indexes/functions are idempotent and named policies
-- and trigger are replaced below. Admin membership is never client-writable.

begin;

create table if not exists public.analytics_events (
  id uuid primary key default gen_random_uuid(),
  event_type text not null,
  event_data jsonb not null,
  user_id uuid references auth.users(id) on delete set null,
  session_id text not null,
  ip_address text,
  user_agent text,
  created_at timestamptz not null default now()
);

create table if not exists public.user_sessions (
  id uuid primary key default gen_random_uuid(),
  session_id text unique not null,
  user_id uuid references auth.users(id) on delete set null,
  started_at timestamptz not null default now(),
  last_active_at timestamptz not null default now(),
  page_count integer not null default 0,
  device_info jsonb,
  location_info jsonb
);

create table if not exists public.admin_users (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade unique not null,
  role text not null default 'admin',
  permissions jsonb not null default '{"analytics": true, "users": false, "products": false}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_analytics_events_event_type on public.analytics_events(event_type);
create index if not exists idx_analytics_events_created_at on public.analytics_events(created_at desc);
create index if not exists idx_analytics_events_user_id on public.analytics_events(user_id);
create index if not exists idx_analytics_events_session_id on public.analytics_events(session_id);
create index if not exists idx_user_sessions_session_id on public.user_sessions(session_id);
create index if not exists idx_user_sessions_user_id on public.user_sessions(user_id);
create index if not exists idx_admin_users_user_id on public.admin_users(user_id);

alter table public.analytics_events enable row level security;
alter table public.user_sessions enable row level security;
alter table public.admin_users enable row level security;

-- SECURITY DEFINER avoids recursive admin_users RLS checks. The empty search
-- path plus schema-qualified objects prevents search_path object substitution.
create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.admin_users
    where user_id = auth.uid()
      and role in ('admin', 'super_admin')
  );
$$;

revoke all on function public.is_admin() from public;
grant execute on function public.is_admin() to authenticated;
drop function if exists public.is_admin(uuid);

create or replace function public.update_session_activity()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  update public.user_sessions
  set last_active_at = now(), page_count = page_count + 1
  where session_id = new.session_id;
  return new;
end;
$$;

revoke all on function public.update_session_activity() from public;

drop trigger if exists update_session_on_page_view on public.analytics_events;
create trigger update_session_on_page_view
  after insert on public.analytics_events
  for each row
  when (new.event_type = 'page_view')
  execute function public.update_session_activity();

-- Remove policies created by both historical analytics scripts before
-- recreating them. PostgreSQL has no CREATE POLICY IF NOT EXISTS syntax.
drop policy if exists "Service role can do everything on analytics_events" on public.analytics_events;
drop policy if exists "Allow anonymous insert on analytics_events" on public.analytics_events;
drop policy if exists "Allow authenticated insert on analytics_events" on public.analytics_events;
drop policy if exists "Users can view their own analytics events" on public.analytics_events;
drop policy if exists "Admins can view all analytics events" on public.analytics_events;
drop policy if exists "Service role can do everything on user_sessions" on public.user_sessions;
drop policy if exists "Allow anonymous insert on user_sessions" on public.user_sessions;
drop policy if exists "Allow anonymous update on user_sessions" on public.user_sessions;
drop policy if exists "Allow authenticated insert on user_sessions" on public.user_sessions;
drop policy if exists "Users can view their own sessions" on public.user_sessions;
drop policy if exists "Admins can view all sessions" on public.user_sessions;
drop policy if exists "Admins can view admin_users table" on public.admin_users;
drop policy if exists "Users can view own admin membership" on public.admin_users;

create policy "Service role can do everything on analytics_events"
  on public.analytics_events for all to service_role
  using (true) with check (true);
create policy "Allow anonymous insert on analytics_events"
  on public.analytics_events for insert to anon with check (true);
create policy "Allow authenticated insert on analytics_events"
  on public.analytics_events for insert to authenticated
  with check (user_id is null or user_id = auth.uid());
create policy "Users can view their own analytics events"
  on public.analytics_events for select to authenticated
  using (user_id = auth.uid());
create policy "Admins can view all analytics events"
  on public.analytics_events for select to authenticated
  using (public.is_admin());

create policy "Service role can do everything on user_sessions"
  on public.user_sessions for all to service_role
  using (true) with check (true);
create policy "Allow anonymous insert on user_sessions"
  on public.user_sessions for insert to anon with check (true);
-- The server's public-key client uses an upsert for anonymous and signed-in
-- tracking. This policy permits that telemetry update, but not reads/deletes.
create policy "Allow anonymous update on user_sessions"
  on public.user_sessions for update to anon using (true) with check (true);
create policy "Allow authenticated insert on user_sessions"
  on public.user_sessions for insert to authenticated
  with check (user_id is null or user_id = auth.uid());
create policy "Users can view their own sessions"
  on public.user_sessions for select to authenticated
  using (user_id = auth.uid());
create policy "Admins can view all sessions"
  on public.user_sessions for select to authenticated
  using (public.is_admin());

-- Users may inspect their own admin membership, but cannot grant or change it.
create policy "Users can view own admin membership"
  on public.admin_users for select to authenticated
  using (user_id = auth.uid());

grant usage on schema public to anon, authenticated, service_role;
grant select, insert on public.analytics_events to anon, authenticated;
grant select, insert, update on public.user_sessions to anon, authenticated;
grant select on public.admin_users to authenticated;
grant all on public.analytics_events, public.user_sessions, public.admin_users to service_role;

commit;
