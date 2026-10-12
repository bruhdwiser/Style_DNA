-- Make tanishq.shelar365@gmail.com an admin
-- Run this in Supabase SQL Editor

-- Step 1: Find the user ID for this email
DO $$
DECLARE
    target_user_id UUID;
BEGIN
    -- Get user ID from email
    SELECT id INTO target_user_id
    FROM auth.users
    WHERE email = 'tanishq.shelar365@gmail.com';
    
    -- Check if user exists
    IF target_user_id IS NULL THEN
        RAISE NOTICE 'User with email tanishq.shelar365@gmail.com not found. Please make sure the user is registered.';
    ELSE
        -- Insert or update admin user
        INSERT INTO admin_users (user_id, role, permissions)
        VALUES (
            target_user_id,
            'admin',
            '{"analytics": true, "users": true, "products": true}'::jsonb
        )
        ON CONFLICT (user_id) 
        DO UPDATE SET 
            role = 'admin',
            permissions = '{"analytics": true, "users": true, "products": true}'::jsonb,
            updated_at = NOW();
        
        RAISE NOTICE 'Successfully made tanishq.shelar365@gmail.com an admin!';
        
        -- Show confirmation
        RAISE NOTICE 'User ID: %', target_user_id;
    END IF;
END $$;

-- Verify the admin user was created
SELECT 
    u.email,
    au.role,
    au.permissions,
    au.created_at
FROM admin_users au
JOIN auth.users u ON u.id = au.user_id
WHERE u.email = 'tanishq.shelar365@gmail.com';
