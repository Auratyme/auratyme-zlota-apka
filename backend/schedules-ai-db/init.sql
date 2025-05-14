-- Create tables for schedules-ai

-- Schedules table
CREATE TABLE IF NOT EXISTS schedules (
    schedule_id TEXT PRIMARY KEY,
    user_id TEXT,
    target_date DATE,
    schedule_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Smartwatch data table
CREATE TABLE IF NOT EXISTS smartwatch_data (
    id SERIAL PRIMARY KEY,
    heart_rate_avg INTEGER,
    heart_rate_spikes JSONB,
    steps INTEGER,
    sleep_records JSONB,
    stress_levels JSONB,
    calories_burned INTEGER,
    hrv FLOAT,
    breathing_rate FLOAT,
    body_battery INTEGER,
    sleep_quality INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User data table
CREATE TABLE IF NOT EXISTS user_data (
    id SERIAL PRIMARY KEY,
    age INTEGER,
    job_type TEXT,
    work_start TEXT,
    work_end TEXT,
    has_children BOOLEAN,
    number_of_children INTEGER,
    commute_time INTEGER,
    health_status TEXT,
    hobbies JSONB,
    marital_status TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_schedules_user_id ON schedules(user_id);
CREATE INDEX IF NOT EXISTS idx_schedules_target_date ON schedules(target_date);
CREATE INDEX IF NOT EXISTS idx_schedules_created_at ON schedules(created_at);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to update updated_at timestamp
CREATE TRIGGER update_schedules_updated_at
BEFORE UPDATE ON schedules
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
