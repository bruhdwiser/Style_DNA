-- Debug Script - Run this in Supabase SQL Editor to check everything

-- 1. Check if admin_users table exists
SELECT EXISTS (
   SELECT FROM information_schema.tables 
   WHERE table_schema = 'public' 
   AND table_name = 'admin_users'
) as admin_table_exists;

-- 2. Check if analytics_events table exists
SELECT EXISTS (
   SELECT FROM information_schema.tables 
   WHERE table_schema = 'public' 
   AND table_name = 'analytics_events'
) as analytics_table_exists;

-- 3. Check if you exist in auth.users
SELECT id, email, created_at 
FROM auth.users 
WHERE email = 'tanishq.shelar365@gmail.com';

-- 4. Check if you're in admin_users table
SELECT 
    au.id,
    au.user_id,
    au.role,
    au.permissions,
    au.created_at,
    u.email
FROM admin_users au
JOIN auth.users u ON u.id = au.user_id
WHERE u.email = 'tanishq.shelar365@gmail.com';

-- 5. List ALL admin users (to see if table is working)
SELECT 
    au.role,
    au.permissions,
    u.email
FROM admin_users au
JOIN auth.users u ON u.id = au.user_id;

-- 6. Check RLS policies on admin_users
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies
WHERE tablename = 'admin_users';
