-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Service role can do everything on analytics_events" ON analytics_events;
DROP POLICY IF EXISTS "Users can view their own analytics events" ON analytics_events;
DROP POLICY IF EXISTS "Admins can view all analytics events" ON analytics_events;
DROP POLICY IF EXISTS "Service role can do everything on user_sessions" ON user_sessions;
DROP POLICY IF EXISTS "Users can view their own sessions" ON user_sessions;
DROP POLICY IF EXISTS "Admins can view all sessions" ON user_sessions;
DROP POLICY IF EXISTS "Admins can view admin_users table" ON admin_users;

-- Drop existing triggers and functions
DROP TRIGGER IF EXISTS update_session_on_page_view ON analytics_events;
DROP FUNCTION IF EXISTS update_session_activity();
DROP FUNCTION IF EXISTS is_admin(UUID);

-- Analytics Events Table
CREATE TABLE IF NOT EXISTS analytics_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type TEXT NOT NULL,
  event_data JSONB NOT NULL,
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  session_id TEXT NOT NULL,
  ip_address TEXT,
  user_agent TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User Sessions Table
CREATE TABLE IF NOT EXISTS user_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id TEXT UNIQUE NOT NULL,
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  last_active_at TIMESTAMPTZ DEFAULT NOW(),
  page_count INTEGER DEFAULT 0,
  device_info JSONB,
  location_info JSONB
);

-- Admin Users Table (for role-based access)
CREATE TABLE IF NOT EXISTS admin_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE NOT NULL,
  role TEXT NOT NULL DEFAULT 'admin',
  permissions JSONB DEFAULT '{"analytics": true, "users": false, "products": false}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_analytics_events_event_type ON analytics_events(event_type);
CREATE INDEX IF NOT EXISTS idx_analytics_events_created_at ON analytics_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_events_user_id ON analytics_events(user_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_session_id ON analytics_events(session_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_admin_users_user_id ON admin_users(user_id);

-- Enable RLS
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;

-- Analytics Events Policies
CREATE POLICY "Service role can do everything on analytics_events"
  ON analytics_events FOR ALL TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "Allow anonymous insert on analytics_events"
  ON analytics_events FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Allow authenticated insert on analytics_events"
  ON analytics_events FOR INSERT TO authenticated
  WITH CHECK (true);

CREATE POLICY "Users can view their own analytics events"
  ON analytics_events FOR SELECT TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "Admins can view all analytics events"
  ON analytics_events FOR SELECT TO authenticated
  USING (
    EXISTS (SELECT 1 FROM admin_users WHERE admin_users.user_id = auth.uid())
  );

-- User Sessions Policies
CREATE POLICY "Service role can do everything on user_sessions"
  ON user_sessions FOR ALL TO service_role
  USING (true) WITH CHECK (true);

CREATE POLICY "Allow anonymous insert on user_sessions"
  ON user_sessions FOR INSERT TO anon
  WITH CHECK (true);

CREATE POLICY "Allow anonymous update on user_sessions"
  ON user_sessions FOR UPDATE TO anon
  USING (true) WITH CHECK (true);

CREATE POLICY "Allow authenticated insert on user_sessions"
  ON user_sessions FOR INSERT TO authenticated
  WITH CHECK (true);

CREATE POLICY "Users can view their own sessions"
  ON user_sessions FOR SELECT TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "Admins can view all sessions"
  ON user_sessions FOR SELECT TO authenticated
  USING (
    EXISTS (SELECT 1 FROM admin_users WHERE admin_users.user_id = auth.uid())
  );

-- Admin Users Policies
CREATE POLICY "Admins can view admin_users table"
  ON admin_users FOR SELECT TO authenticated
  USING (
    EXISTS (SELECT 1 FROM admin_users WHERE admin_users.user_id = auth.uid())
  );

-- Function to check if user is admin
CREATE OR REPLACE FUNCTION is_admin(user_uuid UUID)
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (SELECT 1 FROM admin_users WHERE user_id = user_uuid);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to automatically update last_active_at
CREATE OR REPLACE FUNCTION update_session_activity()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE user_sessions
  SET last_active_at = NOW(), page_count = page_count + 1
  WHERE session_id = NEW.session_id;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update session activity on page view
CREATE TRIGGER update_session_on_page_view
  AFTER INSERT ON analytics_events
  FOR EACH ROW WHEN (NEW.event_type = 'page_view')
  EXECUTE FUNCTION update_session_activity();

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO authenticated, anon;
GRANT SELECT ON analytics_events TO authenticated, anon;
GRANT INSERT ON analytics_events TO authenticated, anon;
GRANT SELECT ON user_sessions TO authenticated, anon;
GRANT INSERT, UPDATE ON user_sessions TO authenticated, anon;
GRANT SELECT ON admin_users TO authenticated;
