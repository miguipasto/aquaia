-- Create user for app
CREATE USER usr_aquaia WITH PASSWORD '<APP_PASSWORD>';

-- Grant privileges to the user
GRANT CONNECT ON DATABASE aquaia TO usr_aquaia;

-- Schema-level privileges
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO usr_aquaia;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO usr_aquaia;
