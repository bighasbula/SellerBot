import os
from dotenv import load_dotenv
import telebot
from telebot import types
from supabase_utils import (
    save_photosession_registration_to_supabase, 
    update_photosession_payment_status, 
    get_photosession_registration_by_id, 
    get_latest_photosession_registration_by_telegram_id, 
    fetch_photosession_registrations,
    get_plan_by_id,
    get_all_plans,
    sync_photosession_registrations_to_drive
)
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
import re

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Easily editable sync interval (in minutes)
SYNC_INTERVAL_MINUTES = 30

bot = telebot.TeleBot(TOKEN)

# Store user registration data temporarily
user_data = {}

# APScheduler setup
scheduler = BackgroundScheduler(timezone=timezone.utc)
scheduler.start()

# Schedule Google Drive sync every SYNC_INTERVAL_MINUTES
scheduler.add_job(sync_photosession_registrations_to_drive, 'interval', minutes=SYNC_INTERVAL_MINUTES)

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

@bot.message_handler(commands=['start'])
def send_welcome(message):
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
    solo_btn = types.InlineKeyboardButton('📸 Solo', callback_data='buy_solo')
    duo_btn = types.InlineKeyboardButton('👯 Duo', callback_data='buy_duo')
    trio_btn = types.InlineKeyboardButton('👩‍👩‍👧 Trio', callback_data='buy_trio')
    extra_btn = types.InlineKeyboardButton('✨ Доп. услуги', callback_data='buy_extra')
    main_menu_btn = types.InlineKeyboardButton('🔙 Главное меню', callback_data='main_menu')
    markup.add(solo_btn, duo_btn, trio_btn, extra_btn, main_menu_btn)
    
    course_text = """Выберите, какую фотосессию вы хотите заказать:"""
    
    bot.send_message(call.message.chat.id, course_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'main_menu')
def handle_main_menu(call):
    markup = types.InlineKeyboardMarkup()
    prices_btn = types.InlineKeyboardButton('🔍 Посмотреть цены', callback_data='see_prices')
    buy_btn = types.InlineKeyboardButton('🛒 Купить фотосессию', callback_data='buy_session')
    markup.add(prices_btn, buy_btn)
    
    welcome_text = """👋 Добро пожаловать!
        Я ваш помощник по бронированию фотосессий. 
        Выберите, что хотите сделать:"""
    
    bot.send_message(call.message.chat.id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'buy_solo')
def handle_buy_solo(call):
    markup = types.InlineKeyboardMarkup()
    solo1_btn = types.InlineKeyboardButton('💫 Solo Базовый', callback_data='buy_solo1')
    solo2_btn = types.InlineKeyboardButton('👑 Premium Solo', callback_data='buy_solo2')
    solo3_btn = types.InlineKeyboardButton('🥇VIP', callback_data='buy_solo3')
    back_btn = types.InlineKeyboardButton('🔙 Назад', callback_data='buy_session')
    
    markup.add(back_btn, solo1_btn, solo2_btn, solo3_btn)
    
    bot.send_message(call.message.chat.id, "Выберите, какую фотосессию вы хотите заказать:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'buy_duo')
def handle_buy_duo(call):
    markup = types.InlineKeyboardMarkup()
    duo_btn = types.InlineKeyboardButton('👩‍👧 Два поколения', callback_data='buy_duo_plan')
    back_btn = types.InlineKeyboardButton('🔙 Назад', callback_data='buy_session')
    
    markup.add(back_btn, duo_btn)
    
    bot.send_message(call.message.chat.id, "Выберите, какую фотосессию вы хотите заказать:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'buy_trio')
def handle_buy_trio(call):
    markup = types.InlineKeyboardMarkup()
    trio_btn = types.InlineKeyboardButton('👩‍👧‍👵 Три поколения', callback_data='buy_trio_plan')
    back_btn = types.InlineKeyboardButton('🔙 Назад', callback_data='buy_session')
    
    markup.add(back_btn, trio_btn)
    
    bot.send_message(call.message.chat.id, "Выберите, какую фотосессию вы хотите заказать:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'buy_extra')
def handle_buy_extra(call):
    markup = types.InlineKeyboardMarkup()
    extra1_btn = types.InlineKeyboardButton('Видео Reels / короткое видео (15–30 сек)', callback_data='buy_extra1')
    extra2_btn = types.InlineKeyboardButton('Дополнительное платье', callback_data='buy_extra2')
    extra3_btn = types.InlineKeyboardButton('Дополнительное обработанное фото', callback_data='buy_extra3')
    back_btn = types.InlineKeyboardButton('🔙 Назад', callback_data='buy_session')
    
    markup.add(back_btn, extra1_btn, extra2_btn, extra3_btn)
    
    bot.send_message(call.message.chat.id, "Выберите, что вы хотите заказать:", reply_markup=markup)

# Handle all plan selections
@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_plan_selection(call):
    plan_id = call.data.replace('buy_', '')
    
    # Handle special cases for duo and trio
    if plan_id == 'duo_plan':
        plan_id = 'duo'
    elif plan_id == 'trio_plan':
        plan_id = 'trio'
    
    plan = get_plan_by_id(plan_id)
    
    if not plan:
        bot.send_message(call.message.chat.id, "❌ План не найден. Пожалуйста, попробуйте снова.")
        return
    
    markup = types.InlineKeyboardMarkup()
    pay_btn = types.InlineKeyboardButton('🔐 Оплатить', callback_data=f'pay_{plan_id}')
    back_btn = types.InlineKeyboardButton('🔙 Назад', callback_data='buy_session')
    markup.add(pay_btn, back_btn)
    
    payment_text = f"""💰 Полная стоимость: ₸{plan['price']:,}
📋 {plan['description']}

💵 Оплата на Kaspi / переводом  
📍 Место бронируется после оплаты

Есть вопросы? Напиши нам в Instagram или WhatsApp:
📸 @wowmotion_photo_video
📞 +7 (706) 651-22-93, +7 (705) 705-82-75
Мы на связи и рады помочь!"""
    
    bot.send_message(call.message.chat.id, payment_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('pay_'))
def handle_payment_initiation(call):
    plan_id = call.data.replace('pay_', '')
    chat_id = call.message.chat.id
    
    # Store user data
    user_data[chat_id] = {'type': plan_id}
    
    bot.send_message(chat_id, "Для регистрации на фотосессию, пожалуйста, напишите ваше полное имя:")
    bot.register_next_step_handler_by_chat_id(chat_id, process_full_name)

def process_full_name(message):
    chat_id = message.chat.id
    user_data[chat_id]['full_name'] = message.text
    bot.send_message(chat_id, "Пожалуйста, напишите свой номер телефона:")
    bot.register_next_step_handler_by_chat_id(chat_id, process_phone)

def process_phone(message):
    chat_id = message.chat.id
    phone = message.text.strip()
    
    # Validate phone number
    if not validate_phone_number(phone):
        bot.send_message(chat_id, "🚫 Пожалуйста, введите корректный номер телефона (пример: +77011234567)")
        bot.register_next_step_handler_by_chat_id(chat_id, process_phone)
        return
    
    # Format phone number to standard format
    formatted_phone = format_phone_number(phone)
    user_data[chat_id]['phone'] = formatted_phone
    user_data[chat_id]['telegram_username'] = message.from_user.username
    
    # Save photosession registration to Supabase
    success = save_photosession_registration_to_supabase(user_data[chat_id], chat_id, message.from_user.username)
    
    if success:
        # Fetch the registration ID from the database
        registration = get_latest_photosession_registration_by_telegram_id(chat_id)
        
        if registration and registration.get('id'):
            registration_id = registration['id']
            user_data[chat_id]['registration_id'] = registration_id
            print(f"Retrieved registration ID from database: {registration_id}")
        else:
            print("Warning: Could not retrieve registration ID from database")
            user_data[chat_id]['registration_id'] = None
        
        # Get plan details for payment instructions
        plan = get_plan_by_id(user_data[chat_id]['type'])
        
        bot.send_message(chat_id, "✅ Регистрация на фотосессию прошла успешно!")
        
        # Send payment instructions
        payment_instructions = f"""💳 ИНСТРУКЦИИ ПО ОПЛАТЕ

💰 Стоимость: ₸{plan['price']:,}

📱 Оплата через Kaspi:
• Ссылка: https://pay.kaspi.kz/pay/s6llvgtb
• Получатель: WowMotion
• Назначение: Фотосессия {plan['name']}

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
            📞 +7 (706) 651-22-93, +7 (705) 705-82-75
            Мы на связи и рады помочь!""")
            
            # Notify admin about new photosession registration with photo
            admin_chat_id = os.getenv('ADMIN_CHAT_ID')
            if admin_chat_id:
                try:
                    admin_chat_id_int = int(admin_chat_id)
                    registration_id = user_data[chat_id].get('registration_id')
                    plan = get_plan_by_id(user_data[chat_id]['type'])
                    
                    # Create inline keyboard with confirmation button
                    markup = None
                    if registration_id:
                        markup = types.InlineKeyboardMarkup()
                        confirm_btn = types.InlineKeyboardButton(
                            '✅ Подтвердить оплату', 
                            callback_data=f'confirm_{registration_id}'
                        )
                        markup.add(confirm_btn)
                    
                    # Send registration details
                    registration_text = f"""📸 Новая регистрация на фотосессию!

👤 Имя: {user_data[chat_id]['full_name']}
📱 Телефон: {user_data[chat_id]['phone']}
🆔 Username: @{user_data[chat_id]['telegram_username']}
📚 План: {plan['name']}
💰 Стоимость: ₸{plan['price']:,}
💳 Статус: Ожидает подтверждения оплаты
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
        success = update_photosession_payment_status(registration_id)
        
        if success:
            # Get registration details to notify the user
            registration = get_photosession_registration_by_id(registration_id)
            
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

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    if chat_id in user_data:
        # This is a payment receipt for photosession registration
        process_payment_receipt(message)
    else:
        bot.send_message(chat_id, "Пожалуйста, используйте команду /start для начала работы с ботом.")

# TESTING: Command to manually trigger Google Drive sync
@bot.message_handler(commands=['test_sync'])
def test_sync(message):
    bot.send_message(message.chat.id, "🔄 Starting manual Google Drive sync...")
    sync_photosession_registrations_to_drive()
    bot.send_message(message.chat.id, "✅ Manual sync completed!")

if __name__ == "__main__":
    print("Bot is polling...")
    print(f"Google Drive sync scheduled every {SYNC_INTERVAL_MINUTES} minutes")
    bot.polling(none_stop=True)
