# Railway Deployment Guide

This guide will help you deploy your photosession seller bot to Railway.

## Prerequisites

1. GitHub account with your bot repository
2. Railway account (sign up at [railway.app](https://railway.app))
3. All environment variables configured

## Step 1: Prepare Your Repository

1. Make sure all files are committed to your GitHub repository:
   ```bash
   git add .
   git commit -m "Prepare for Railway deployment"
   git push origin main
   ```

2. Verify these files are in your repository:
   - `bot.py` (main bot file)
   - `supabase_utils.py` (database utilities)
   - `requirements.txt` (dependencies)
   - `Procfile` (Railway process definition)
   - `runtime.txt` (Python version)
   - `.gitignore` (excludes sensitive files)

## Step 2: Deploy to Railway

1. **Connect to GitHub**:
   - Go to [Railway Dashboard](https://railway.app/dashboard)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your photosession bot repository

2. **Configure the Service**:
   - Railway will automatically detect it's a Python project
   - The `Procfile` will tell Railway to run `python bot.py`
   - Railway will install dependencies from `requirements.txt`

## Step 3: Configure Environment Variables

1. **In Railway Dashboard**:
   - Go to your project
   - Click on the service
   - Go to "Variables" tab
   - Add all required environment variables:

   ```env
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   SUPABASE_URL=your_supabase_project_url
   SUPABASE_API_KEY=your_supabase_anon_key
   ADMIN_CHAT_ID=your_admin_telegram_chat_id
   GOOGLE_DRIVE_FOLDER_ID=your_google_drive_folder_id
   GOOGLE_SERVICE_ACCOUNT_JSON={"type": "service_account", ...}
   ```

2. **Important**: For the `GOOGLE_SERVICE_ACCOUNT_JSON`, paste the entire JSON content as a single line.

## Step 4: Deploy and Monitor

1. **Deploy**:
   - Railway will automatically deploy when you push to GitHub
   - Or click "Deploy" in the Railway dashboard

2. **Monitor Logs**:
   - Go to "Deployments" tab to see build logs
   - Go to "Logs" tab to see runtime logs
   - Look for these success messages:
     ```
     Bot is polling...
     Google Drive sync scheduled every 30 minutes
     ```

3. **Test the Bot**:
   - Send `/start` to your bot
   - Test the `/test_sync` command for Google Drive sync

## Step 5: Set Up Custom Domain (Optional)

1. **Custom Domain**:
   - Go to "Settings" tab
   - Add your custom domain if needed
   - Configure DNS records as instructed

## Troubleshooting

### Common Issues

1. **Build Fails**:
   - Check that all dependencies are in `requirements.txt`
   - Verify Python version in `runtime.txt`
   - Check build logs for specific errors

2. **Bot Not Responding**:
   - Verify `TELEGRAM_BOT_TOKEN` is correct
   - Check runtime logs for errors
   - Ensure bot is polling (should see "Bot is polling...")

3. **Database Connection Issues**:
   - Verify `SUPABASE_URL` and `SUPABASE_API_KEY`
   - Check that your Supabase project is active
   - Ensure the `photosession_registrations` table exists

4. **Google Drive Sync Issues**:
   - Verify `GOOGLE_DRIVE_FOLDER_ID` and `GOOGLE_SERVICE_ACCOUNT_JSON`
   - Check that service account has access to the folder
   - Look for sync errors in logs

### Logs to Monitor

- **Startup**: Should see "Bot is polling..." and "Google Drive sync scheduled..."
- **Registration**: Should see "Photosession registration saved to Supabase"
- **Sync**: Should see "Successfully synced photosession registrations to Google Drive"
- **Errors**: Any exceptions will be logged with full stack traces

### Environment Variable Format

For Railway, ensure environment variables are properly formatted:

```env
# Correct format
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"your-project","private_key":"-----BEGIN PRIVATE KEY-----\nYOUR_KEY\n-----END PRIVATE KEY-----\n","client_email":"your-service@your-project.iam.gserviceaccount.com"}

# Avoid line breaks in the JSON
```

## Scaling and Monitoring

1. **Auto-scaling**: Railway automatically scales based on traffic
2. **Monitoring**: Use Railway's built-in monitoring dashboard
3. **Logs**: All logs are available in real-time
4. **Restarts**: Railway automatically restarts on failures

## Cost Optimization

1. **Free Tier**: Railway offers a generous free tier
2. **Usage Monitoring**: Monitor your usage in the Railway dashboard
3. **Optimization**: The bot is lightweight and should stay within free limits

## Security Best Practices

1. **Environment Variables**: Never commit sensitive data to Git
2. **Service Account**: Use minimal permissions for Google Drive access
3. **Monitoring**: Regularly check logs for any security issues
4. **Updates**: Keep dependencies updated for security patches

## Support

If you encounter issues:
1. Check Railway's documentation
2. Review the logs for specific error messages
3. Verify all environment variables are set correctly
4. Test locally before deploying
