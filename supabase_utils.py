import os
import requests
import json
from dotenv import load_dotenv
from datetime import datetime, timezone
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import io
import pandas as pd

load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_API_KEY')

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# Hardcoded plans for photosessions
PHOTOSESSION_PLANS = {
    'solo1': {
        'id': 'solo1',
        'name': 'Solo Базовый',
        'price': 200000,
        'description': '1 парящее платье, макияж и прическа, все снимки без обработки, 5 обработанных фотографий'
    },
    'solo2': {
        'id': 'solo2', 
        'name': 'Premium Solo',
        'price': 280000,
        'description': '1 парящее платье, макияж и причёска, все снимки без обработки, 12 обработанных фото'
    },
    'solo3': {
        'id': 'solo3',
        'name': 'VIP',
        'price': 360000,
        'description': '2 парящих платья, макияж и причёска, все снимки без обработки, 25 обработанных фото'
    },
    'duo': {
        'id': 'duo',
        'name': 'Два поколения',
        'price': 360000,
        'description': '1 парящее платье на каждую участницу, макияж и прическа для обеих, 15 обработанных фото'
    },
    'trio': {
        'id': 'trio',
        'name': 'Три поколения',
        'price': 440000,
        'description': '1 парящее платье на каждую участницу, макияж и прическа для трёх, 20 обработанных фото'
    },
    'extra1': {
        'id': 'extra1',
        'name': 'Видео Reels',
        'price': 70000,
        'description': 'Короткое видео (15–30 сек)'
    },
    'extra2': {
        'id': 'extra2',
        'name': 'Дополнительное платье',
        'price': 25000,
        'description': 'Дополнительное парящее платье'
    },
    'extra3': {
        'id': 'extra3',
        'name': 'Дополнительное фото',
        'price': 5000,
        'description': 'Дополнительное обработанное фото'
    }
}

def get_service_account_credentials():
    """
    Get Google service account credentials from environment variable.
    Returns credentials object for Google APIs.
    """
    service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    if not service_account_json:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON not found in environment variables")
    
    try:
        # Parse the JSON string from environment variable
        service_account_info = json.loads(service_account_json)
        return service_account.Credentials.from_service_account_info(service_account_info)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: {e}")

def get_drive_service():
    """Get Google Drive service instance"""
    creds = get_service_account_credentials()
    return build('drive', 'v3', credentials=creds)

def find_file_metadata(service, folder_id, file_name):
    """Find file metadata in Google Drive folder"""
    query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    files = results.get('files', [])
    if not files:
        raise FileNotFoundError(f"File '{file_name}' not found in folder '{folder_id}'")
    return files[0]  # returns dict with id, name, mimeType

def download_excel_file(service, file_id, mime_type, local_path):
    """Download file from Google Drive"""
    if mime_type == 'application/vnd.google-apps.spreadsheet':
        # Export Google Sheet as Excel
        request = service.files().export_media(fileId=file_id, mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    else:
        # Download native Excel file
        request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(local_path, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.close()

def update_excel_sheet(local_path, registrations):
    """Update Excel sheet with new data"""
    # Load Excel file
    with pd.ExcelWriter(local_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        df = pd.DataFrame(registrations)
        df.to_excel(writer, sheet_name='Sheet1', index=False)
    # openpyxl preserves other sheets/styles

def upload_excel_file(service, file_id, local_path, mime_type):
    """Upload file back to Google Drive"""
    if mime_type == 'application/vnd.google-apps.spreadsheet':
        # Re-upload as Google Sheet (convert Excel to Google Sheet)
        media = MediaFileUpload(local_path, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        updated = service.files().update(
            fileId=file_id,
            media_body=media,
            body={'mimeType': 'application/vnd.google-apps.spreadsheet'}
        ).execute()
    else:
        # Replace Excel file
        media = MediaFileUpload(local_path, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        updated = service.files().update(fileId=file_id, media_body=media).execute()
    return updated

def sync_photosession_registrations_to_drive():
    """Sync photosession registrations to Google Drive Excel file"""
    try:
        # 1. Fetch photosession registrations from Supabase
        photosession_registrations = fetch_photosession_registrations()
        
        # 2. Authenticate and find file in Drive
        service = get_drive_service()
        folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        
        try:
            file_metadata = find_file_metadata(service, folder_id, 'PhotosessionRegistrations.xlsx')
            file_id = file_metadata['id']
            mime_type = file_metadata['mimeType']
            # 3. Download the file (export if Google Sheet)
            local_path = 'PhotosessionRegistrations.xlsx'
            download_excel_file(service, file_id, mime_type, local_path)
        except FileNotFoundError:
            print("📝 Creating new PhotosessionRegistrations.xlsx file in Google Drive...")
            # Create a new Excel file with photosession registrations data
            df = pd.DataFrame(photosession_registrations)
            df.to_excel('PhotosessionRegistrations.xlsx', index=False)
            
            # Upload the new file to Google Drive
            file_metadata = {
                'name': 'PhotosessionRegistrations.xlsx',
                'parents': [folder_id]
            }
            media = MediaFileUpload('PhotosessionRegistrations.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            file_id = file.get('id')
            print(f"✅ Created new file with ID: {file_id}")
            return
        
        # 4. Update Sheet1
        update_excel_sheet(local_path, photosession_registrations)
        # 5. Upload back to Drive (replace original, convert if needed)
        upload_excel_file(service, file_id, local_path, mime_type)
        print(f"✅ Successfully synced photosession registrations to 'PhotosessionRegistrations.xlsx' in Google Drive.")
    except Exception as e:
        print(f"❌ Error syncing photosession registrations to Google Drive: {e}")

def get_plan_by_id(plan_id):
    """Get plan details by plan ID"""
    return PHOTOSESSION_PLANS.get(plan_id)

def get_all_plans():
    """Get all available plans"""
    return PHOTOSESSION_PLANS

def save_photosession_registration_to_supabase(user_data, telegram_id, username=None):
    """
    Save photosession registration to Supabase photosession_registrations table.
    Returns True if successful, False otherwise.
    
    Required table schema:
    CREATE TABLE photosession_registrations (
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
    """
    print("save_photosession_registration_to_supabase called with:", user_data, telegram_id)
    
    PHOTOSESSION_REGISTRATIONS_ENDPOINT = f"{SUPABASE_URL}/rest/v1/photosession_registrations"
    
    # Get plan details
    plan_id = user_data.get('type')
    plan = get_plan_by_id(plan_id)
    
    if not plan:
        print(f"Invalid plan_id: {plan_id}")
        return False
    
    data = {
        "full_name": user_data.get("full_name"),
        "phone_number": user_data.get("phone"),
        "telegram_username": f"@{username}" if username else None,
        "telegram_id": str(telegram_id),
        "plan_id": plan_id,
        "plan_name": plan['name'],
        "is_paid": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    print("Photosession registration data to send:", data)
    print("Endpoint:", PHOTOSESSION_REGISTRATIONS_ENDPOINT)
    print("Headers:", HEADERS)
    
    try:
        response = requests.post(PHOTOSESSION_REGISTRATIONS_ENDPOINT, json=data, headers=HEADERS)
        print("Supabase response:", response.status_code, response.text)
        
        if response.status_code in (200, 201):
            print("Photosession registration saved to Supabase.")
            return True
        else:
            print(f"Failed to save photosession registration: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print(f"Exception during Supabase photosession registration: {e}")
        return False

def update_photosession_payment_status(registration_id):
    """
    Update photosession registration payment status to paid in Supabase.
    """
    print(f"update_photosession_payment_status called with registration_id: {registration_id}")
    
    PHOTOSESSION_REGISTRATIONS_ENDPOINT = f"{SUPABASE_URL}/rest/v1/photosession_registrations"
    
    data = {
        "is_paid": True
    }
    
    print("Payment update data to send:", data)
    print("Endpoint:", f"{PHOTOSESSION_REGISTRATIONS_ENDPOINT}?id=eq.{registration_id}")
    
    try:
        response = requests.patch(
            f"{PHOTOSESSION_REGISTRATIONS_ENDPOINT}?id=eq.{registration_id}",
            json=data,
            headers=HEADERS
        )
        print("Supabase response:", response.status_code, response.text)
        if response.status_code in (200, 204):
            print("Photosession payment status updated in Supabase.")
            return True
        else:
            print(f"Failed to update payment status: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print(f"Exception during payment status update: {e}")
        return False

def get_photosession_registration_by_id(registration_id):
    """
    Get photosession registration details by ID from Supabase.
    """
    PHOTOSESSION_REGISTRATIONS_ENDPOINT = f"{SUPABASE_URL}/rest/v1/photosession_registrations"
    
    try:
        response = requests.get(
            f"{PHOTOSESSION_REGISTRATIONS_ENDPOINT}?id=eq.{registration_id}",
            headers=HEADERS
        )
        response.raise_for_status()
        registrations = response.json()
        return registrations[0] if registrations else None
    except Exception as e:
        print(f"Exception getting photosession registration: {e}")
        return None

def get_latest_photosession_registration_by_telegram_id(telegram_id):
    """
    Get the latest photosession registration for a specific telegram_id from Supabase.
    """
    PHOTOSESSION_REGISTRATIONS_ENDPOINT = f"{SUPABASE_URL}/rest/v1/photosession_registrations"
    
    try:
        response = requests.get(
            f"{PHOTOSESSION_REGISTRATIONS_ENDPOINT}?telegram_id=eq.{telegram_id}&order=created_at.desc&limit=1",
            headers=HEADERS
        )
        response.raise_for_status()
        registrations = response.json()
        return registrations[0] if registrations else None
    except Exception as e:
        print(f"Exception getting latest photosession registration: {e}")
        return None

def fetch_photosession_registrations():
    """
    Fetch all photosession registrations from the Supabase 'photosession_registrations' table.
    Returns a list of dicts.
    """
    PHOTOSESSION_REGISTRATIONS_ENDPOINT = f"{SUPABASE_URL}/rest/v1/photosession_registrations"
    
    try:
        response = requests.get(PHOTOSESSION_REGISTRATIONS_ENDPOINT, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Exception fetching photosession registrations: {e}")
        return []
