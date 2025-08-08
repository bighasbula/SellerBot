-- Create photosession_registrations table for the photosession seller bot
CREATE TABLE IF NOT EXISTS photosession_registrations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    full_name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    telegram_username TEXT,
    telegram_id TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    plan_name TEXT NOT NULL,
    is_paid BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster queries by telegram_id
CREATE INDEX IF NOT EXISTS idx_photosession_registrations_telegram_id 
ON photosession_registrations(telegram_id);

-- Create index for faster queries by payment status
CREATE INDEX IF NOT EXISTS idx_photosession_registrations_is_paid 
ON photosession_registrations(is_paid);

-- Create index for faster queries by creation date
CREATE INDEX IF NOT EXISTS idx_photosession_registrations_created_at 
ON photosession_registrations(created_at);

-- Enable Row Level Security (RLS) for better security
ALTER TABLE photosession_registrations ENABLE ROW LEVEL SECURITY;

-- Create policy to allow all operations (you can modify this based on your security needs)
CREATE POLICY "Allow all operations on photosession_registrations" ON photosession_registrations
    FOR ALL USING (true);

-- Optional: Create a view for easy querying of paid registrations
CREATE OR REPLACE VIEW paid_photosession_registrations AS
SELECT 
    id,
    full_name,
    phone_number,
    telegram_username,
    telegram_id,
    plan_id,
    plan_name,
    created_at
FROM photosession_registrations 
WHERE is_paid = true;

-- Optional: Create a view for easy querying of pending payments
CREATE OR REPLACE VIEW pending_photosession_payments AS
SELECT 
    id,
    full_name,
    phone_number,
    telegram_username,
    telegram_id,
    plan_id,
    plan_name,
    created_at
FROM photosession_registrations 
WHERE is_paid = false;
