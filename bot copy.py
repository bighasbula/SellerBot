import os
from dotenv import load_dotenv
import telebot
from telebot import types
from supabase_utilscopy import save_registration_to_supabase, get_webinar_dates, fetch_registrations, get_service_account_credentials, save_course_registration_to_supabase, update_course_payment_status, get_course_registration_by_id, get_latest_course_registration_by_telegram_id, fetch_course_registrations
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
import io
import requests
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import re

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Easily editable sync interval (in minutes)
SYNC_INTERVAL_MINUTES = 30
EXCEL_FILE_NAME = 'WebinarRegistrations.xlsx'
EXCEL_FILE_NAME_COURSES = 'CoursesRegistrations.xlsx'



bot = telebot.TeleBot(TOKEN)

# Store user registration data temporarily
user_data = {}

# Input validation functions
def validate_phone_number(phone):
    """
    Validate Kazakhstan phone number format.
    Accepts: +7 707 123 45 67, 87071234567, 8 (707) 123-45-67, +77071234567
    """
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Check for valid Kazakhstan mobile number patterns
    patterns = [
        r'^\+77\d{9}$',  # +77071234567
        r'^87\d{9}$',    # 87071234567
    ]
    
    for pattern in patterns:
        if re.match(pattern, cleaned):
            return True
    
    return False

def validate_email(email):
    """
    Validate email format using regex.
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def format_phone_number(phone):
    """
    Format phone number to standard Kazakhstan format: +7 7XX XXX XX XX
    """
    # Remove all non-digit characters
    cleaned = re.sub(r'[^\d]', '', phone)
    
    # If it starts with 8, replace with +7
    if cleaned.startswith('8'):
        cleaned = '7' + cleaned[1:]
    
    # If it doesn't start with 7, add +7
    if not cleaned.startswith('7'):
        cleaned = '7' + cleaned
    
    # Format as +7 7XX XXX XX XX
    if len(cleaned) == 11 and cleaned.startswith('7'):
        return f"+7 {cleaned[1:4]} {cleaned[4:7]} {cleaned[7:9]} {cleaned[9:11]}"
    
    return phone  # Return original if can't format

# APScheduler setup
scheduler = BackgroundScheduler(timezone=timezone.utc)
scheduler.start()



# Google Drive sync functions
def get_drive_service():
    creds = get_service_account_credentials()
    return build('drive', 'v3', credentials=creds)

def find_file_metadata(service, folder_id, file_name):
    query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    files = results.get('files', [])
    if not files:
        raise FileNotFoundError(f"File '{file_name}' not found in folder '{folder_id}'")
    return files[0]  # returns dict with id, name, mimeType

def download_excel_file(service, file_id, mime_type, local_path):
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
    # Load Excel file
    with pd.ExcelWriter(local_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        df = pd.DataFrame(registrations)
        df.to_excel(writer, sheet_name='Sheet1', index=False)
    # openpyxl preserves other sheets/styles

def upload_excel_file(service, file_id, local_path, mime_type):
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

def sync_course_registrations_to_drive():
    """Sync course registrations to Google Drive Excel file"""
    try:
        # 1. Fetch course registrations from Supabase
        course_registrations = fetch_course_registrations()
        # 2. Authenticate and find file in Drive
        service = get_drive_service()
        folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        
        try:
            file_metadata = find_file_metadata(service, folder_id, 'EXCEL_FILE_NAME_COURSES')
            file_id = file_metadata['id']
            mime_type = file_metadata['mimeType']
            # 3. Download the file (export if Google Sheet)
            local_path = 'CoursesRegistrations.xlsx'
            download_excel_file(service, file_id, mime_type, local_path)
        except FileNotFoundError:
            print("📝 Creating new CoursesRegistrations.xlsx file in Google Drive...")
            # Create a new Excel file with course registrations data
            df = pd.DataFrame(course_registrations)
            df.to_excel('CoursesRegistrations.xlsx', index=False)
            
            # Upload the new file to Google Drive
            file_metadata = {
                'name': 'CoursesRegistrations.xlsx',
                'parents': [folder_id]
            }
            media = MediaFileUpload('CoursesRegistrations.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            file_id = file.get('id')
            print(f"✅ Created new file with ID: {file_id}")
            return
        
        # 4. Update Sheet1
        update_excel_sheet(local_path, course_registrations)
        # 5. Upload back to Drive (replace original, convert if needed)
        upload_excel_file(service, file_id, local_path, mime_type)
        print(f"✅ Successfully synced course registrations to 'CoursesRegistrations.xlsx' in Google Drive.")
    except Exception as e:
        print(f"❌ Error syncing course registrations to Google Drive: {e}")

def sync_registrations_to_drive():
    """Sync webinar registrations to Google Drive Excel file"""
    try:
        # 1. Fetch registrations from Supabase
        registrations = fetch_registrations()
        # 2. Authenticate and find file in Drive
        service = get_drive_service()
        folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        file_metadata = find_file_metadata(service, folder_id, EXCEL_FILE_NAME)
        file_id = file_metadata['id']
        mime_type = file_metadata['mimeType']
        # 3. Download the file (export if Google Sheet)
        local_path = EXCEL_FILE_NAME
        download_excel_file(service, file_id, mime_type, local_path)
        # 4. Update Sheet1
        update_excel_sheet(local_path, registrations)
        # 5. Upload back to Drive (replace original, convert if needed)
        upload_excel_file(service, file_id, local_path, mime_type)
        print(f"✅ Successfully synced registrations to '{EXCEL_FILE_NAME}' in Google Drive.")
    except Exception as e:
        print(f"❌ Error syncing to Google Drive: {e}")

def sync_all_to_drive():
    """Sync both webinar and course registrations to Google Drive"""
    print("🔄 Starting sync of all registrations to Google Drive...")
    sync_registrations_to_drive()
    sync_course_registrations_to_drive()
    print("✅ All sync operations completed.")


# Schedule Google Drive sync every SYNC_INTERVAL_MINUTES
scheduler.add_job(sync_all_to_drive, 'interval', minutes=SYNC_INTERVAL_MINUTES)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Send circle video if file_id is available
    
    
    markup = types.InlineKeyboardMarkup()
    prices_btn = types.InlineKeyboardButton('🔍 Посмотреть цены', callback_data='see_prices')
    buy_btn = types.InlineKeyboardButton('🛒 Купить фотосессию', callback_data='buy_session')
    markup.add(prices_btn, buy_btn)
    
    welcome_text = """👋 Добро пожаловать!
        Я ваш помощник по бронированию фотосессий. 
        Выберите, что хотите сделать:"""
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'see_prices')
def handle_see_prices(call):

    #if CIRCLE_VIDEO_FILE_ID2:
        #try:
            #bot.send_video_note(call.message.chat.id, CIRCLE_VIDEO_FILE_ID2)
        #except Exception as e:
            #print(f"Error sending circle video: {e}")
            # Continue with normal flow even if video fails
    
    # Small delay to let video load
    #import time
    #time.sleep(1)
    prices_text = """📸 Пакеты фотосъёмки в парящих платьях — Астана

⸻

💫 Solo Базовый — ₸200 000 

Включено:
• 1 парящее платье
• Макияж и прическа
• Все снимки без обработки (в течение 3-4 дней после съемки) 
• 5 обработанных фотографий (в течение 4 недель после съемки)
• Ассистент (входит во все пакеты - помогает надевать платье, подгоняет под фигуру, работает с подолом и образом во время съемки) 

⸻

👑 Premium Solo — ₸280 000 

Включено:
• 1 парящее платье
• Макияж и причёска
• Все снимки без обработки (в течение 3-4 дней после съемки) 
• 12 обработанных фото (приоритетная обработка, в течение 10 дней после съемки)
• Ассистент (входит во все пакеты - полный функционал) 

⸻

🥇VIP — ₸360 000 

Включено:
• 2 парящих платья (смена образа во время съемки) 
• Макияж и причёска
• Все снимки без обработки (в течение 3-4 дней после съемки) 
• 25 обработанных фото (в течение 4 недель)
• Приоритетная дата съемки
• Ассистент (входит во все пакеты - полный функционал) 

⸻

👩‍👧 Два поколения — ₸360 000

Включено:
• 1 парящее платье на каждую участницу
• Макияж и прическа для обеих
• Все снимки без обработки (в течение 3–4 дней после съемки)
• 15 обработанных фото (в течение 4 недель)
• Ассистент (помощь с образами, подолом, позированием)

👩‍👧‍👵 Три поколения — ₸440 000

Включено:
• 1 парящее платье на каждую участницу
• Макияж и прическа для трёх
• Все снимки без обработки (в течение 3–4 дней после съемки)
• 20 обработанных фото (в течение 4 недель)
• Ассистент (работает с каждой участницей)

🎯 Дополнительные услуги (по желанию)

• Видео Reels / короткое видео (15–30 сек): ₸70 000  
• Дополнительное платье: ₸25 000 
• Реквизит (диадема, шары, дым, лепестки и т.п.): ₸10 000 – ₸30 000 
• Дополнительное обработанное фото: ₸5 000 за 1 шт."""

    markup = types.InlineKeyboardMarkup()
    main_menu_btn = types.InlineKeyboardButton('🔙 Главное меню', callback_data='main_menu')
    markup.add(main_menu_btn)
    bot.send_message(call.message.chat.id, prices_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'buy_session')
def handle_buy_session(call):

    

    markup = types.InlineKeyboardMarkup()
    how_btn = types.InlineKeyboardButton('📸 Solo', callback_data='buy_solo')
    program_btn = types.InlineKeyboardButton('👯 Duo', callback_data='buy_duo')
    payment_btn = types.InlineKeyboardButton('👩‍👩‍👧 Trio', callback_data='buy_trio')
    faq_btn = types.InlineKeyboardButton('✨ Доп. услуги', callback_data='buy_extra')
    main_menu_btn = types.InlineKeyboardButton('🔙 Главное меню', callback_data='main_menu')
    markup.add(how_btn, program_btn, payment_btn, faq_btn, main_menu_btn)
    
    course_text = """Выберите, какую фотосессию вы хотите заказать:"""
    
    bot.send_message(call.message.chat.id, course_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'main_menu')
def handle_main_menu(call):
    markup = types.InlineKeyboardMarkup()
    prices_btn = types.InlineKeyboardButton('🔍 Посмотреть цены', callback_data='see_prices')
    buy_btn = types.InlineKeyboardButton('🛒 Купить фотосессию', callback_data='buy_session')
    markup.add(prices_btn, buy_btn)

@bot.callback_query_handler(func=lambda call: call.data == 'buy_duo')
def handle_buy_duo(call):
    markup = types.InlineKeyboardMarkup()
    buy_reg_btn = types.InlineKeyboardButton('👩‍👧 Два поколения', callback_data='buy_duo')
    
    back_btn = types.InlineKeyboardButton('🔙 Назад', callback_data='buy_session')
    
    markup.add(back_btn, buy_reg_btn)
    
    bot.send_message(call.message.chat.id, "Выберите, какую фотосессию вы хотите заказать:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'buy_solo')
def handle_buy_solo(call):
    markup = types.InlineKeyboardMarkup()
    solo1_btn = types.InlineKeyboardButton('💫 Solo Базовый', callback_data='buy_solo1')
    solo2_btn = types.InlineKeyboardButton('👑 Premium Solo', callback_data='buy_solo2')
    solo3_btn = types.InlineKeyboardButton('🥇VIP', callback_data='buy_solo3')
    back_btn = types.InlineKeyboardButton('🔙 Назад', callback_data='buy_session')
    
    markup.add(back_btn, solo1_btn, solo2_btn, solo3_btn)
    
    
    bot.send_message(call.message.chat.id, "Выберите, какую фотосессию вы хотите заказать:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'buy_trio')
def handle_buy_trio(call):
    markup = types.InlineKeyboardMarkup()
    buy_reg_btn = types.InlineKeyboardButton('👩‍👧‍👵 Три поколения', callback_data='buy_trio')
    
    back_btn = types.InlineKeyboardButton('🔙 Назад', callback_data='buy_session')
    
    markup.add(back_btn, buy_reg_btn)
    
    bot.send_message(call.message.chat.id, "Выберите, какую фотосессию вы хотите заказать:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'buy_extra')
def handle_buy_extra(call):
    markup = types.InlineKeyboardMarkup()
    buy_reg_btn = types.InlineKeyboardButton('Видео Reels / короткое видео (15–30 сек)', callback_data='buy_extra1')
    buy_reg_btn2 = types.InlineKeyboardButton('Дополнительное платье', callback_data='buy_extra2')
    buy_reg_btn3 = types.InlineKeyboardButton('Дополнительное обработанное фото', callback_data='buy_extra3')
    back_btn = types.InlineKeyboardButton('🔙 Назад', callback_data='buy_session')
    
    markup.add(back_btn, buy_reg_btn, buy_reg_btn2, buy_reg_btn3)
    
    bot.send_message(call.message.chat.id, "Выберите, что вы хотите заказать:", reply_markup=markup)



@bot.callback_query_handler(func=lambda call: call.data == 'buy_solo1')
def handle_buy_solo1(call):
    markup = types.InlineKeyboardMarkup()
    pay_btn = types.InlineKeyboardButton('🔐 Оплатить', callback_data='buy_solo1_pay')
    back_btn = types.InlineKeyboardButton('Назад', callback_data='buy_session')
    markup.add(pay_btn, back_btn)
    
    payment_text = """💰 Полная стоимость фотосессии: ₸200 000  
💵 Оплата на Kaspi / переводом  
📍 Место бронируется после оплаты

Есть вопросы? Напиши нам в Instagram или WhatsApp:
📸 @wowmotion_photo_video
📞 +7 (706) 651-22-93, +7 (705) 705-82-75
Мы на связи и рады помочь!"""
    
    bot.send_message(call.message.chat.id, payment_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'buy_solo1_pay')
def handle_buy_solo1_pay(call):
    chat_id = call.message.chat.id
    user_data[chat_id] = {'type': 'solo1'}
    bot.send_message(chat_id, "Для регистрации на фотосессию, пожалуйста, напишите ваше полное имя:")
    bot.register_next_step_handler_by_chat_id(chat_id, process_course_full_name)

@bot.callback_query_handler(func=lambda call: call.data == 'buy_solo2')
def handle_buy_solo2(call):
    markup = types.InlineKeyboardMarkup()
    pay_btn = types.InlineKeyboardButton('🔐 Оплатить', callback_data='buy_solo2_pay')
    back_btn = types.InlineKeyboardButton('Назад', callback_data='buy_session')
    markup.add(pay_btn, back_btn)
    
    payment_text = """💰 Полная стоимость фотосессии: ₸280 000  
💵 Оплата на Kaspi / переводом  
📍 Место бронируется после оплаты

Есть вопросы? Напиши нам в Instagram или WhatsApp:
📸 @wowmotion_photo_video
📞 +7 (706) 651-22-93, +7 (705) 705-82-75
Мы на связи и рады помочь!"""
    
    bot.send_message(call.message.chat.id, payment_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'buy_solo2_pay')
def handle_buy_solo2_pay(call):
    chat_id = call.message.chat.id
    user_data[chat_id] = {'type': 'solo2'}
    bot.send_message(chat_id, "Для регистрации на фотосессию, пожалуйста, напишите ваше полное имя:")
    bot.register_next_step_handler_by_chat_id(chat_id, process_course_full_name)





def process_course_full_name(message):
    chat_id = message.chat.id
    user_data[chat_id]['full_name'] = message.text
    bot.send_message(chat_id, "Пожалуйста, напишите свой номер телефона:")
    bot.register_next_step_handler_by_chat_id(chat_id, process_course_phone)

def process_course_phone(message):
    chat_id = message.chat.id
    phone = message.text.strip()
    
    # Validate phone number
    if not validate_phone_number(phone):
        bot.send_message(chat_id, "🚫 Пожалуйста, введите корректный номер телефона (пример: +77011234567)")
        bot.register_next_step_handler_by_chat_id(chat_id, process_course_phone)
        return
    
    # Format phone number to standard format
    formatted_phone = format_phone_number(phone)
    user_data[chat_id]['phone'] = formatted_phone
    user_data[chat_id]['telegram_username'] = message.from_user.username
    
    # Save course registration to Supabase
    success = save_course_registration_to_supabase(user_data[chat_id], chat_id, message.from_user.username)
    
    if success:
        # Fetch the registration ID from the database
        registration = get_latest_course_registration_by_telegram_id(chat_id)
        
        if registration and registration.get('id'):
            registration_id = registration['id']
            user_data[chat_id]['registration_id'] = registration_id
            print(f"Retrieved registration ID from database: {registration_id}")
        else:
            print("Warning: Could not retrieve registration ID from database")
            user_data[chat_id]['registration_id'] = None
        
        bot.send_message(chat_id, "✅ Регистрация на курс прошла успешно!")
        
        # Send payment instructions
        payment_instructions = """💳 ИНСТРУКЦИИ ПО ОПЛАТЕ

💰 Стоимость курса: 200,000₸

📱 Оплата через Kaspi:
• Ссылка: https://pay.kaspi.kz/pay/s6llvgtb
• Получатель: WowMotion
• Назначение: Фотосессия


📸 После оплаты, пожалуйста, отправьте фото чека для подтверждения."""
        
        bot.send_message(chat_id, payment_instructions)
        bot.send_message(chat_id, "📸 Отправьте фото чека об оплате:")
        bot.register_next_step_handler_by_chat_id(chat_id, process_payment_receipt)
    else:
        bot.send_message(chat_id, "⚠️ Что-то пошло не так. Пожалуйста, попробуйте снова позже.")

def process_payment_receipt(message):
    chat_id = message.chat.id
    if message.photo:
        # Get the largest photo size
        photo = message.photo[-1]
        file_id = photo.file_id
        
        try:
            # Download the photo
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # Send confirmation to user
            bot.send_message(chat_id, """✅ Спасибо! Ваш чек получен. Мы проверим оплату и свяжемся с вами в течение 24 часов.
            Есть вопросы? Напиши нам в Instagram или WhatsApp:
            📸 @wowmotion_photo_video
            📞 [+7 (706) 651-22-93, +7 (705) 705-82-75]
            Мы на связи и рады помочь!""")
            
            # Notify admin about new course registration with photo
            admin_chat_id = os.getenv('ADMIN_CHAT_ID')  # Add this to your .env
            if admin_chat_id:
                try:
                    admin_chat_id_int = int(admin_chat_id)
                    registration_id = user_data[chat_id].get('registration_id')
                    
                    # Create inline keyboard with confirmation button (only if we have a real ID)
                    markup = None
                    if registration_id:
                        markup = types.InlineKeyboardMarkup()
                        confirm_btn = types.InlineKeyboardButton(
                            '✅ Подтвердить оплату', 
                            callback_data=f'confirm_{registration_id}'
                        )
                        markup.add(confirm_btn)
                    
                    # Send registration details
                    registration_text = f"""🎓 Новая регистрация на фотосессию!

👤 Имя: {user_data[chat_id]['full_name']}
📱 Телефон: {user_data[chat_id]['phone']}
🆔 Username: @{user_data[chat_id]['telegram_username']}
📚 План: Solo Базовый
💰 Статус: Ожидает подтверждения оплаты
📅 Дата регистрации: {datetime.now().strftime('%d.%m.%Y %H:%M')}"""
                    
                    if registration_id:
                        registration_text += f"\n🆔 ID регистрации: {registration_id}"
                    else:
                        registration_text += "\n⚠️ ID регистрации: Не удалось получить (требуется ручная проверка)"
                    
                    # Send the payment receipt photo with confirmation button
                    bot.send_photo(
                        admin_chat_id_int, 
                        downloaded_file, 
                        caption=registration_text,
                        reply_markup=markup
                    )
                    
                except Exception as e:
                    print(f"Error sending to admin: {e}")
            else:
                print("ADMIN_CHAT_ID not set in environment variables")
                
        except Exception as e:
            print(f"Error processing payment receipt: {e}")
            bot.send_message(chat_id, "⚠️ Ошибка при обработке чека. Пожалуйста, попробуйте снова.")
    else:
        bot.send_message(chat_id, "Пожалуйста, отправьте фото чека об оплате.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
def handle_payment_confirmation(call):
    """Handle payment confirmation from admin"""
    try:
        # Extract registration ID from callback data
        registration_id = call.data.replace('confirm_', '')
        
        # Update payment status in Supabase
        success = update_course_payment_status(registration_id)
        
        if success:
            # Get registration details to notify the user
            registration = get_course_registration_by_id(registration_id)
            
            # Notify admin
            bot.answer_callback_query(call.id, "✅ Платёж подтверждён и записан в базу данных.")
            
            # Update the message to show it's confirmed
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=call.message.caption + "\n\n✅ ПЛАТЁЖ ПОДТВЕРЖДЁН",
                reply_markup=None  # Remove the button
            )
            
            # Notify the original user
            if registration and registration.get('telegram_id'):
                try:
                    user_chat_id = int(registration['telegram_id'])
                    bot.send_message(
                        user_chat_id, 
                        "🎉 Ваша оплата подтверждена! Спасибо за регистрацию. Мы свяжемся с вами в ближайшее время."
                    )
                except Exception as e:
                    print(f"Error notifying user: {e}")
        else:
            bot.answer_callback_query(call.id, "❌ Ошибка при подтверждении платежа.")
            
    except Exception as e:
        print(f"Error in payment confirmation: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка.")



# TESTING: Command to manually trigger Google Drive sync
@bot.message_handler(commands=['test_sync'])
def test_sync(message):
    bot.send_message(message.chat.id, "🔄 Starting manual Google Drive sync...")
    sync_all_to_drive()
    bot.send_message(message.chat.id, "✅ Manual sync completed!")

# TESTING: Command to manually trigger course registrations sync only
@bot.message_handler(commands=['test_course_sync'])
def test_course_sync(message):
    bot.send_message(message.chat.id, "🔄 Starting manual course registrations sync...")
    sync_course_registrations_to_drive()
    bot.send_message(message.chat.id, "✅ Course registrations sync completed!")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    if chat_id in user_data and user_data[chat_id].get('type') == 'course':
        # This is a payment receipt for course registration
        process_payment_receipt(message)
    else:
        bot.send_message(chat_id, "Пожалуйста, используйте команду /start для начала работы с ботом.")

if __name__ == "__main__":
    print("Bot is polling...")
    print(f"Google Drive sync scheduled every {SYNC_INTERVAL_MINUTES} minutes")
    bot.polling(none_stop=True) 