-- Make a user an admin
-- Replace 'user-email@example.com' with the actual user's email

-- First, find the user ID
SELECT id, email FROM auth.users WHERE email = 'user-email@example.com';

-- Then insert into admin_users table (replace USER_ID_HERE with the actual UUID from above)
INSERT INTO admin_users (user_id, role, permissions)
VALUES (
  'USER_ID_HERE',
  'admin',
  '{"analytics": true, "users": true, "products": true}'::jsonb
)
ON CONFLICT (user_id) DO UPDATE
SET role = 'admin',
    permissions = '{"analytics": true, "users": true, "products": true}'::jsonb,
    updated_at = NOW();

-- Verify the admin user was created
SELECT 
  au.*,
  u.email
FROM admin_users au
JOIN auth.users u ON u.id = au.user_id;

-- Quick way to make current user admin (if you're logged in):
-- Run this in Supabase SQL editor while logged in
INSERT INTO admin_users (user_id, role, permissions)
SELECT 
  auth.uid(),
  'admin',
  '{"analytics": true, "users": true, "products": true}'::jsonb
WHERE auth.uid() IS NOT NULL
ON CONFLICT (user_id) DO UPDATE
SET role = 'admin',
    permissions = '{"analytics": true, "users": true, "products": true}'::jsonb,
    updated_at = NOW();
