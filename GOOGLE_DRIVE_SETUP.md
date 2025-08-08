# Google Drive Integration Setup Guide

This guide will help you set up automatic Google Drive sync for your photosession registrations.

## Prerequisites

1. Google Cloud Platform account
2. Google Drive account
3. Python environment with the required dependencies

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click on it and press "Enable"

## Step 2: Create Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in the service account details:
   - Name: `photosession-bot-sync`
   - Description: `Service account for photosession bot Google Drive sync`
4. Click "Create and Continue"
5. Skip the optional steps and click "Done"

## Step 3: Generate Service Account Key

1. Click on the created service account
2. Go to the "Keys" tab
3. Click "Add Key" > "Create New Key"
4. Choose "JSON" format
5. Download the JSON file
6. **Important**: Keep this file secure and never commit it to version control

## Step 4: Set Up Google Drive Folder

1. Go to [Google Drive](https://drive.google.com/)
2. Create a new folder for your photosession registrations
3. Right-click on the folder and select "Share"
4. Add your service account email (from the JSON file) with "Editor" permissions
5. Copy the folder ID from the URL:
   - The URL will look like: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
   - Copy the `FOLDER_ID_HERE` part

## Step 5: Configure Environment Variables

1. Copy the contents of the downloaded JSON file
2. In your `.env` file, add:
   ```env
   GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here
   GOOGLE_SERVICE_ACCOUNT_JSON={"type": "service_account", ...}
   ```

## Step 6: Test the Integration

1. Run your bot
2. Use the `/test_sync` command to manually trigger a sync
3. Check your Google Drive folder for the `PhotosessionRegistrations.xlsx` file

## File Structure

The bot will create and maintain a file called `PhotosessionRegistrations.xlsx` in your Google Drive folder with the following columns:

- `id`: Registration UUID
- `full_name`: Customer's full name
- `phone_number`: Customer's phone number
- `telegram_username`: Customer's Telegram username
- `telegram_id`: Customer's Telegram ID
- `plan_id`: Selected plan ID
- `plan_name`: Selected plan name
- `is_paid`: Payment status (true/false)
- `created_at`: Registration timestamp

## Automatic Sync

The bot automatically syncs data every 30 minutes. You can modify the sync interval by changing the `SYNC_INTERVAL_MINUTES` variable in `bot.py`.

## Troubleshooting

### Common Issues

1. **"GOOGLE_SERVICE_ACCOUNT_JSON not found"**
   - Make sure the JSON is properly formatted in your `.env` file
   - Ensure there are no extra quotes or formatting issues

2. **"File not found in folder"**
   - Check that the folder ID is correct
   - Ensure the service account has access to the folder

3. **"Permission denied"**
   - Make sure the service account has "Editor" permissions on the folder
   - Check that the Google Drive API is enabled

4. **"Invalid JSON"**
   - Copy the entire JSON content from the downloaded file
   - Don't modify the JSON structure

### Manual Sync Testing

Use the `/test_sync` command in your bot to manually trigger a sync and see detailed logs.

## Security Notes

- Never commit the service account JSON to version control
- Use environment variables for all sensitive data
- Regularly rotate service account keys
- Monitor API usage in Google Cloud Console

## API Quotas

Google Drive API has quotas:
- 1,000 requests per 100 seconds per user
- 10,000 requests per 100 seconds per project

For most use cases, this is more than sufficient for the 30-minute sync interval.
