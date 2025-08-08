# Photosession Seller Bot

A Telegram bot for selling photosession packages with dynamic pricing and Supabase integration, featuring automatic Google Drive sync.

## Features

- 📸 **Multiple Photosession Plans**: Solo, Duo, Trio, and additional services
- 💳 **Payment Processing**: Kaspi integration with receipt verification
- 👨‍💼 **Admin Panel**: Payment confirmation and registration management
- 📊 **Database Integration**: Supabase for data storage and management
- 📱 **User-Friendly Interface**: Intuitive Telegram bot interface
- ☁️ **Google Drive Sync**: Automatic export to Google Sheets every 30 minutes
- 🚀 **Railway Ready**: Optimized for deployment on Railway

## Plans Available

### Solo Packages
- **Solo Базовый** - ₸200,000 (1 dress, makeup, 5 edited photos)
- **Premium Solo** - ₸280,000 (1 dress, makeup, 12 edited photos)
- **VIP** - ₸360,000 (2 dresses, makeup, 25 edited photos)

### Group Packages
- **Два поколения** - ₸360,000 (2 dresses, makeup for both, 15 edited photos)
- **Три поколения** - ₸440,000 (3 dresses, makeup for three, 20 edited photos)

### Additional Services
- **Видео Reels** - ₸70,000 (15-30 second video)
- **Дополнительное платье** - ₸25,000 (extra dress)
- **Дополнительное фото** - ₸5,000 (extra edited photo)

## Quick Start

### Option 1: Deploy to Railway (Recommended)

1. **Fork/Clone** this repository to your GitHub account
2. **Sign up** for [Railway](https://railway.app)
3. **Connect** your GitHub repository to Railway
4. **Configure** environment variables in Railway dashboard
5. **Deploy** - Railway will automatically build and deploy your bot

📖 **Detailed Railway deployment guide**: See [DEPLOYMENT.md](DEPLOYMENT.md)

### Option 2: Local Development

1. **Clone** the repository
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Set up environment**: Copy `env_template.txt` to `.env` and fill in your values
4. **Set up database**: Run `database_setup.sql` in your Supabase project
5. **Set up Google Drive**: Follow [GOOGLE_DRIVE_SETUP.md](GOOGLE_DRIVE_SETUP.md)
6. **Run the bot**: `python bot.py`

## Environment Variables

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Supabase Configuration
SUPABASE_URL=your_supabase_project_url_here
SUPABASE_API_KEY=your_supabase_anon_key_here

# Admin Configuration
ADMIN_CHAT_ID=your_admin_telegram_chat_id_here

# Google Drive Configuration
GOOGLE_DRIVE_FOLDER_ID=your_google_drive_folder_id_here
GOOGLE_SERVICE_ACCOUNT_JSON={"type": "service_account", ...}
```

## Database Schema

The `photosession_registrations` table includes:

- `id` (UUID): Primary key
- `full_name` (TEXT): Customer's full name
- `phone_number` (TEXT): Customer's phone number
- `telegram_username` (TEXT): Customer's Telegram username
- `telegram_id` (TEXT): Customer's Telegram ID
- `plan_id` (TEXT): Selected plan ID
- `plan_name` (TEXT): Selected plan name
- `is_paid` (BOOLEAN): Payment status
- `created_at` (TIMESTAMP): Registration timestamp

## Bot Flow

1. **Welcome**: User starts bot with `/start`
2. **Plan Selection**: User chooses from available plans
3. **Registration**: User provides name and phone number
4. **Payment Instructions**: Bot provides Kaspi payment link
5. **Receipt Upload**: User uploads payment receipt
6. **Admin Review**: Admin receives notification with receipt
7. **Payment Confirmation**: Admin confirms payment via button
8. **User Notification**: User receives confirmation message

## Admin Features

- Receive notifications for new registrations
- View payment receipts
- Confirm payments with one click
- Automatic user notification upon confirmation

## Google Drive Integration

### Automatic Sync
- Data is automatically exported to Google Sheets every 30 minutes
- File: `PhotosessionRegistrations.xlsx` in your configured Google Drive folder
- Includes all registration data with proper formatting

### Manual Sync
- Use `/test_sync` command to manually trigger a sync
- Useful for testing and immediate data export

### File Structure
The Google Sheets file contains all registration data with columns:
- Registration ID, Customer Name, Phone, Telegram Info
- Plan Details, Payment Status, Registration Date

## File Structure

```
DressBot/
├── bot.py                    # Main bot file
├── supabase_utils.py         # Database utilities
├── database_setup.sql        # Database schema
├── requirements.txt          # Python dependencies
├── Procfile                  # Railway process definition
├── runtime.txt               # Python version for Railway
├── railway.json              # Railway configuration
├── .gitignore                # Git ignore rules
├── env_template.txt          # Environment variables template
├── GOOGLE_DRIVE_SETUP.md     # Google Drive setup guide
├── DEPLOYMENT.md             # Railway deployment guide
└── README.md                # This file
```

## Customization

### Adding New Plans

1. Update the `PHOTOSESSION_PLANS` dictionary in `supabase_utils.py`
2. Add corresponding callback handlers in `bot.py`

### Modifying Payment Flow

1. Update payment instructions in the `process_phone` function
2. Modify admin notification format in `process_payment_receipt`

### Sync Interval

1. Change the `SYNC_INTERVAL_MINUTES` variable in `bot.py`
2. Default is 30 minutes, can be adjusted as needed

### Database Queries

Use the provided utility functions in `supabase_utils.py`:
- `save_photosession_registration_to_supabase()`
- `update_photosession_payment_status()`
- `get_photosession_registration_by_id()`
- `fetch_photosession_registrations()`

## Security Features

- Phone number validation for Kazakhstan format
- Row Level Security (RLS) enabled in Supabase
- Admin-only payment confirmation
- Secure environment variable handling
- Google Drive service account authentication

## Deployment

### Railway (Recommended)
- **Automatic scaling** based on traffic
- **Free tier** available
- **Easy environment variable management**
- **Real-time logs and monitoring**

### Other Platforms
The bot can be deployed to any platform that supports Python:
- Heroku
- DigitalOcean App Platform
- AWS Lambda
- Google Cloud Run

## Support

For questions or issues:
- 📸 Instagram: @wowmotion_photo_video
- 📞 Phone: +7 (706) 651-22-93, +7 (705) 705-82-75

## License

This project is proprietary and confidential. 