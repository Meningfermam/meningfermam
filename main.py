import os
import time
import random
import telebot
from telebot import types
import psycopg2
from psycopg2 import pool

# Environment Variable'lardan ma'lumotlarni olish
DATABASE_URL = os.environ.get('DATABASE_URL')
API_TOKEN = os.environ.get('BOT_TOKEN')

bot = telebot.TeleBot(API_TOKEN)

# Bot username'ini bir marta olish
BOT_USERNAME = None
try:
    BOT_USERNAME = bot.get_me().username
except Exception:
    pass

ANIMALS = {
    'tovuq': {'name': '🐔 Tovuq', 'price': 24000, 'daily': 2400, 'total': 72000},
    'quyon': {'name': '🐇 Quyon', 'price': 45000, 'daily': 4500, 'total': 135000},
    'goz': {'name': "🪿 G'oz", 'price': 115000, 'daily': 12000, 'total': 360000},
    'echki': {'name': '🐐 Echki', 'price': 200000, 'daily': 25000, 'total': 750000},
    'qoy': {'name': "🐑 Qo'y", 'price': 325000, 'daily': 3750, 'total': 1125000},
    'sigir': {'name': '🐄 Sigir', 'price': 450000, 'daily': 50000, 'total': 1500000},
    'ot': {'name': '🐎 Ot', 'price': 1200000, 'daily': 150000, 'total': 4500000},
    'tuya': {'name': '🐪 Tuya', 'price': 2400000, 'daily': 300000, 'total': 9000000},
    'buqa': {'name': '🐂 Buqa', 'price': 3600000, 'daily': 425000, 'total': 12750000},
}

ADMIN_ID = 925576047
CARD_NUMBER = '5614681858174125 vs 4231200220385677'

# Database Connection Pool
db_pool = pool.SimpleConnectionPool(1, 20, DATABASE_URL, sslmode='require')

def get_db():
    return db_pool.getconn()

def release_db(conn):
    db_pool.putconn(conn)

def init_db():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # Jadvallarni yaratish
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    balance BIGINT DEFAULT 0,
                    referrals INT DEFAULT 0,
                    referrer_id BIGINT DEFAULT NULL,
                    last_bonus BIGINT DEFAULT 0,
                    state VARCHAR(50) DEFAULT NULL
                );
            ''')
            
            # Agar eski baza bo'lib state ustuni bo'lmasa, uni majburiy qo'shish
            cursor.execute('''
                ALTER TABLE users ADD COLUMN IF NOT EXISTS state VARCHAR(50) DEFAULT NULL;
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_animals (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                    animal_key VARCHAR(50),
                    buy_time BIGINT,
                    last_harvest BIGINT
                );
            ''')
            conn.commit()
    finally:
        release_db(conn)

def set_user_state(user_id, state):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute('UPDATE users SET state = %s WHERE user_id = %s;', (state, user_id))
            conn.commit()
    finally:
        release_db(conn)

def get_user_state(user_id):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT state FROM users WHERE user_id = %s;', (user_id,))
            row = cursor.fetchone()
            return row[0] if row else None
    finally:
        release_db(conn)

def get_user(user_id, referrer_id=None):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT balance, referrals FROM users WHERE user_id = %s;', (user_id,))
            user = cursor.fetchone()

            if not user:
                ref_id = None
                if referrer_id and str(referrer_id).isdigit():
                    ref_id = int(referrer_id)
                    if ref_id == user_id:
                        ref_id = None

                cursor.execute(
                    'INSERT INTO users (user_id, balance, referrals, referrer_id, last_bonus) VALUES (%s, 0, 0, %s, 0);',
                    (user_id, ref_id)
                )

                if ref_id:
                    cursor.execute('UPDATE users SET referrals = referrals + 1 WHERE user_id = %s;', (ref_id,))
                    try:
                        bot.send_message(
                            ref_id,
                            "🎉 *Sizning referal havolangiz orqali yangi foydalanuvchi botga qo'shildi!*",
                            parse_mode='Markdown'
                        )
                    except Exception:
                        pass

                conn.commit()
                user = (0, 0)
            return user
    finally:
        release_db(conn)

def get_user_animals_summary(user_id):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT animal_key FROM user_animals WHERE user_id = %s;', (user_id,))
            rows = cursor.fetchall()

        if not rows:
            return 'Mavjud emas'

        counts = {}
        for r in rows:
            key = r[0]
            counts[key] = counts.get(key, 0) + 1

        res = [f"{ANIMALS[key]['name']} ({count} ta)" for key, count in counts.items()]
        return ', '.join(res)
    finally:
        release_db(conn)

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('🐮 Hayvon sotib olish')
    markup.row('👤 Profil', '🔗 Referal')
    markup.row('💸 Pul kiritish', '💰 Pul yechish')
    markup.row('🌾 Mening hayvonlarim (Fermam)', '🎁 Kunlik bonus')
    return markup

def get_shop_inline():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton('🐔 Tovuq', callback_data='view_tovuq'),
        types.InlineKeyboardButton('🐇 Quyon', callback_data='view_quyon'),
    )
    markup.row(
        types.InlineKeyboardButton("🪿 G'oz", callback_data='view_goz'),
        types.InlineKeyboardButton('🐐 Echki', callback_data='view_echki'),
    )
    markup.row(
        types.InlineKeyboardButton("🐑 Qo'y", callback_data='view_qoy'),
        types.InlineKeyboardButton('🐄 Sigir', callback_data='view_sigir'),
    )
    markup.row(
        types.InlineKeyboardButton('🐎 Ot', callback_data='view_ot'),
        types.InlineKeyboardButton('🐪 Tuya', callback_data='view_tuya'),
    )
    markup.row(types.InlineKeyboardButton('🐂 Buqa', callback_data='view_buqa'))
    return markup

@bot.message_handler(commands=['start'])
def cmd_start(message):
    args = message.text.split()
    referrer_id = args[1].replace('r', '') if len(args) > 1 and args[1].startswith('r') else None

    get_user(message.from_user.id, referrer_id)
    set_user_state(message.from_user.id, None)
    
    bot.send_message(
        message.chat.id,
        '🌾 *Mening Fermam botiga xush kelibsiz!*',
        reply_markup=get_main_menu(),
        parse_mode='Markdown',
    )

# --- ADMIN PANEL: BALANS QO'SHISH ---
@bot.message_handler(commands=['add'])
def admin_add_balance(message):
    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split()
    if len(args) < 3:
        bot.send_message(message.chat.id, "⚠️ *Xato format!*\nFoydalanish: `/add USER_ID SUMMA`\n*Masalan:* `/add 123456789 50000`", parse_mode='Markdown')
        return

    target_id = int(args[1])
    amount = int(args[2])

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute('UPDATE users SET balance = balance + %s WHERE user_id = %s;', (amount, target_id))
            if cursor.rowcount == 0:
                bot.send_message(message.chat.id, "❌ Bunday foydalanuvchi topilmadi!", parse_mode='Markdown')
                return
            conn.commit()

        bot.send_message(message.chat.id, f"✅ `{target_id}` foydalanuvchisiga *{amount:,} so'm* qo'shildi!", parse_mode='Markdown')
        
        try:
            bot.send_message(target_id, f"🎉 *Sizning balansingiz {amount:,} so'mga to'ldirildi!*", parse_mode='Markdown')
        except Exception:
            pass
    finally:
        release_db(conn)

@bot.message_handler(func=lambda msg: msg.text == '⬅️ Ortga qaytish')
def back_to_main_menu(message):
    set_user_state(message.from_user.id, None)
    bot.send_message(message.chat.id, '▪️ *Bosh sahifaga xush kelibsiz.*', reply_markup=get_main_menu(), parse_mode='Markdown')

# --- PUL YECHISH TIZIMI ---

@bot.message_handler(func=lambda msg: msg.text == '💰 Pul yechish')
def withdraw_start(message):
    user_id = message.from_user.id
    u = get_user(user_id)
    set_user_state(user_id, 'waiting_for_withdraw')

    text = (
        f"💰 *Pul yechib olish*\n\n"
        f"💳 Sizning balansingiz: *{u[0]:,} so'm*\n"
        f"⚠️ Eng kam yechib olish summasi: *10,000 so'm*\n\n"
        f"Iltimos, yechib olmoqchi bo'lgan summaniz va karta raqamingizni yuboring.\n\n"
        f"📌 *Namuna:* `50000 8600123456789012`"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('⬅️ Ortga qaytish')
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda msg: get_user_state(msg.from_user.id) == 'waiting_for_withdraw')
def handle_withdraw_request(message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 2 or not args[0].isdigit():
        bot.send_message(message.chat.id, "⚠️ *Xato format!*\nNamuna: `50000 8600123456789012`", parse_mode='Markdown')
        return

    amount = int(args[0])
    card = ' '.join(args[1:])

    if amount < 10000:
        bot.send_message(message.chat.id, "❌ *Eng kam pul yechish summasi 10,000 so'm!*", parse_mode='Markdown')
        return

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute('UPDATE users SET balance = balance - %s WHERE user_id = %s AND balance >= %s RETURNING balance;', (amount, user_id, amount))
            updated = cursor.fetchone()

            if not updated:
                bot.send_message(message.chat.id, "❌ *Balansingizda yetarli mablag' yo'q!*", parse_mode='Markdown')
                return

            conn.commit()
    finally:
        release_db(conn)

    set_user_state(user_id, None)
    bot.send_message(message.chat.id, "✅ *Arizangiz qabul qilindi!* Admin tez orada to'lovni amalga oshiradi.", reply_markup=get_main_menu(), parse_mode='Markdown')

    try:
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_w_{user_id}_{amount}"),
            types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_w_{user_id}_{amount}")
        )
        bot.send_message(
            ADMIN_ID,
            f"💸 *Yangi pul yechish so'rovi!*\n\n👤 ID: `{user_id}`\n💰 Summa: *{amount:,} so'm*\n💳 Karta: `{card}`",
            parse_mode='Markdown',
            reply_markup=markup
        )
    except Exception:
        pass

# --- ADMIN TASDIQLASH VA RAD ETISH HANDLERLARI ---

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_w_'))
def approve_withdraw(call):
    if call.from_user.id != ADMIN_ID:
        return

    _, _, user_id, amount = call.data.split('_')
    user_id = int(user_id)
    amount = int(amount)

    bot.edit_message_text(
        f"{call.message.text}\n\n✅ *STATUS: ADMIN TARAFIDAN TO'LANDI*",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )

    try:
        bot.send_message(
            user_id,
            f"✅ *Sizning {amount:,} so'm pul yechish so'rovingiz tasdiqlandi va kartangizga o'tkazildi!*",
            parse_mode='Markdown'
        )
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_w_'))
def reject_withdraw(call):
    if call.from_user.id != ADMIN_ID:
        return

    _, _, user_id, amount = call.data.split('_')
    user_id = int(user_id)
    amount = int(amount)

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute('UPDATE users SET balance = balance + %s WHERE user_id = %s;', (amount, user_id))
            conn.commit()
    finally:
        release_db(conn)

    bot.edit_message_text(
        f"{call.message.text}\n\n❌ *STATUS: RAD ETILDI (Balans qaytarildi)*",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )

    try:
        bot.send_message(
            user_id,
            f"❌ *Sizning {amount:,} so'm pul yechish so'rovingiz rad etildi.* Mablag' balansingizga qaytarildi.",
            parse_mode='Markdown'
        )
    except Exception:
        pass

# --- QOLGAN FUNKSIYALAR ---

@bot.message_handler(func=lambda msg: msg.text == '🎁 Kunlik bonus')
def daily_bonus_handler(message):
    user_id = message.from_user.id
    now = int(time.time())
    cooldown = 24 * 60 * 60

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT last_bonus FROM users WHERE user_id = %s;', (user_id,))
            row = cursor.fetchone()
            last_bonus = row[0] if row else 0

            if now - last_bonus < cooldown:
                remaining_time = cooldown - (now - last_bonus)
                hours = remaining_time // 3600
                minutes = (remaining_time % 3600) // 60
                bot.send_message(message.chat.id, f"⏳ *Bonus olgansiz!* Keyingi vaqt: *{hours} soat {minutes} daqiqa*", parse_mode='Markdown')
                return

            bonus_amount = random.randint(500, 5000)
            cursor.execute('UPDATE users SET balance = balance + %s, last_bonus = %s WHERE user_id = %s;', (bonus_amount, now, user_id))
            conn.commit()

        bot.send_message(message.chat.id, f"🎁 *Sizga {bonus_amount:,} so'm bonus berildi!*", parse_mode='Markdown')
    finally:
        release_db(conn)

@bot.message_handler(func=lambda msg: msg.text == '🌾 Mening hayvonlarim (Fermam)')
def show_farm(message):
    user_id = message.from_user.id
    now = int(time.time())

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT id, animal_key, buy_time, last_harvest FROM user_animals WHERE user_id = %s;', (user_id,))
            animals = cursor.fetchall()

        if not animals:
            bot.send_message(message.chat.id, "🌾 *Sizda hali hech qanday hayvon yo'q.*", parse_mode='Markdown')
            return

        total_uncollected = 0
        farm_details = []

        for a_id, key, buy_time, last_harvest in animals:
            max_duration = 30 * 86400
            active_time = min(now, buy_time + max_duration)

            if active_time > last_harvest:
                seconds_passed = active_time - last_harvest
                daily_income = ANIMALS[key]['daily']
                earned = int(seconds_passed * (daily_income / 86400))
                total_uncollected += earned

            farm_details.append(f"• {ANIMALS[key]['name']}")

        text = (
            f"🌾 *Sizning fermangiz:*\n\n" + '\n'.join(farm_details) +
            f"\n\n💰 *Yig'ilgan daromad:* {total_uncollected:,} so'm"
        )
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("📥 Daromadni yig'ish", callback_data='collect_income'))
        bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
    finally:
        release_db(conn)

@bot.callback_query_handler(func=lambda call: call.data == 'collect_income')
def collect_income(call):
    user_id = call.from_user.id
    now = int(time.time())

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute('SELECT id, animal_key, buy_time, last_harvest FROM user_animals WHERE user_id = %s;', (user_id,))
            animals = cursor.fetchall()
            total_uncollected = 0

            for a_id, key, buy_time, last_harvest in animals:
                max_duration = 30 * 86400
                active_time = min(now, buy_time + max_duration)

                if active_time > last_harvest:
                    earned = int((active_time - last_harvest) * (ANIMALS[key]['daily'] / 86400))
                    total_uncollected += earned
                    cursor.execute('UPDATE user_animals SET last_harvest = %s WHERE id = %s;', (active_time, a_id))

            if total_uncollected > 0:
                cursor.execute('UPDATE users SET balance = balance + %s WHERE user_id = %s;', (total_uncollected, user_id))
                conn.commit()
                bot.answer_callback_query(call.id, f"✅ {total_uncollected:,} so'm o'tkazildi!", show_alert=True)
                bot.edit_message_text(f"🎉 *Barcha daromadlar yig'ildi:* {total_uncollected:,} so'm", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
            else:
                bot.answer_callback_query(call.id, "⚠️ Hozircha daromad yo'q!", show_alert=True)
    finally:
        release_db(conn)

@bot.message_handler(func=lambda msg: msg.text == '👤 Profil')
def show_profile(message):
    u = get_user(message.from_user.id)
    animals_text = get_user_animals_summary(message.from_user.id)
    text = (
        f"👤 *Sizning kabinetingiz:*\n\n"
        f"🆔 *ID:* `{message.from_user.id}`\n"
        f"💰 *Balans:* {u[0]:,} so'm\n"
        f"👥 *Takliflar:* {u[1]} ta\n"
        f"🌾 *Hayvonlar:* {animals_text}"
    )
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda msg: msg.text == '🔗 Referal')
def show_ref(message):
    username = BOT_USERNAME or bot.get_me().username
    ref_link = f'https://t.me/{username}?start=r{message.from_user.id}'
    bot.send_message(message.chat.id, f"Sizning referal havolangiz:\n{ref_link}")

@bot.message_handler(func=lambda msg: msg.text == '💸 Pul kiritish')
def deposit_start(message):
    text = f"💸 *Quyidagi kartaga to'lov qiling:*\n\n💳 `{CARD_NUMBER}`"
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("✅ To'lovni amalga oshirdim", callback_data='pay_done'))
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'pay_done')
def pay_done_callback(call):
    set_user_state(call.from_user.id, 'waiting_for_check')
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('⬅️ Ortga qaytish')
    bot.send_message(call.message.chat.id, "👨‍💼 *To'lov chekini yuboring.*", parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(content_types=['photo', 'document'], func=lambda msg: get_user_state(msg.from_user.id) == 'waiting_for_check')
def handle_check_upload(message):
    set_user_state(message.from_user.id, None)
    bot.send_message(message.chat.id, "✅ *Chek qabul qilindi.*", reply_markup=get_main_menu(), parse_mode='Markdown')
    if message.photo:
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"ID: `{message.from_user.id}`")

@bot.message_handler(func=lambda msg: msg.text == '🐮 Hayvon sotib olish')
def show_shop(message):
    bot.send_message(message.chat.id, '🛒 *Hayvonni tanlang:*', reply_markup=get_shop_inline(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('view_'))
def view_animal(call):
    key = call.data.split('_')[1]
    item = ANIMALS[key]
    text = f"Nomi: {item['name']}\n\n▫️ Narxi: {item['price']:,} so'm\n▫️ Kunlik: {item['daily']:,} so'm"
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton('💸 Sotib olish', callback_data=f'buy_{key}'))
    markup.row(types.InlineKeyboardButton('⬅️ Orqaga', callback_data='back_to_shop'))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_shop')
def back_shop(call):
    bot.edit_message_text('🛒 *Hayvonni tanlang:*', call.message.chat.id, call.message.message_id, reply_markup=get_shop_inline(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def buy_animal(call):
    key = call.data.split('_')[1]
    user_id = call.from_user.id
    item = ANIMALS[key]
    now = int(time.time())

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute('UPDATE users SET balance = balance - %s WHERE user_id = %s AND balance >= %s RETURNING balance;', (item['price'], user_id, item['price']))
            res = cursor.fetchone()

            if not res:
                bot.answer_callback_query(call.id, '❌ Balans yetarli emas!', show_alert=True)
                return

            cursor.execute('INSERT INTO user_animals (user_id, animal_key, buy_time, last_harvest) VALUES (%s, %s, %s, %s);', (user_id, key, now, now))

            cursor.execute('SELECT referrer_id FROM users WHERE user_id = %s;', (user_id,))
            ref_row = cursor.fetchone()
            if ref_row and ref_row[0]:
                ref_id = ref_row[0]
                bonus = int(item['price'] * 0.10)
                cursor.execute('UPDATE users SET balance = balance + %s WHERE user_id = %s;', (bonus, ref_id))

            conn.commit()
    finally:
        release_db(conn)

    bot.answer_callback_query(call.id, f"✅ {item['name']} sotib olindi!", show_alert=True)
    bot.send_message(call.message.chat.id, f"🎉 *Tabriklaymiz! {item['name']} sotib olindi!*", parse_mode='Markdown')

if __name__ == '__main__':
    init_db()
    print('Bot tayyor va ishga tushdi!')
    bot.infinity_polling()
