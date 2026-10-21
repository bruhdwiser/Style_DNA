-- Optional: grant the admin role to an existing Supabase account.
-- Run only after create-analytics-tables-clean.sql, and replace the email below.
-- Keep backend/.env ADMIN_EMAILS in sync if you use that allowlist as well.

do $$
declare
  target_email text := 'user-email@example.com'; -- replace before running
  target_user_id uuid;
begin
  select id into target_user_id
  from auth.users
  where lower(email) = lower(target_email)
  limit 1;

  if target_user_id is null then
    raise exception 'No Supabase Auth user found for %. Sign up first, then rerun this script.', target_email;
  end if;

  insert into public.admin_users (user_id, role, permissions)
  values (
    target_user_id,
    'admin',
    '{"analytics": true, "users": true, "products": true}'::jsonb
  )
  on conflict (user_id) do update
    set role = excluded.role,
        permissions = excluded.permissions,
        updated_at = now();
end $$;

select au.user_id, u.email, au.role, au.permissions, au.created_at
from public.admin_users au
join auth.users u on u.id = au.user_id
where lower(u.email) = lower('user-email@example.com');
