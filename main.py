import os
import re
import time
import telebot
from telebot import types
import psycopg2
from psycopg2 import pool

DATABASE_URL = os.environ.get('DATABASE_URL')
API_TOKEN = os.environ.get('BOT_TOKEN')

bot = telebot.TeleBot(API_TOKEN)

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
    'qoy': {'name': "🐑 Qo'y", 'price': 325000, 'daily': 37500, 'total': 1125000},
    'sigir': {'name': '🐄 Sigir', 'price': 450000, 'daily': 50000, 'total': 1500000},
    'ot': {'name': '🐎 Ot', 'price': 1200000, 'daily': 150000, 'total': 4500000},
    'tuya': {'name': '🐪 Tuya', 'price': 2400000, 'daily': 300000, 'total': 9000000},
    'buqa': {'name': '🐂 Buqa', 'price': 3600000, 'daily': 425000, 'total': 12750000},
}

ADMIN_ID = 925576047
CARD_NUMBER_1 = '5614 6818 5817 4125'
CARD_NUMBER_2 = '4231 2002 2038 5677'
CARD_OWNER = "Ism Familiya"

db_pool = pool.SimpleConnectionPool(1, 20, DATABASE_URL, sslmode='require')

def get_db():
    return db_pool.getconn()

def release_db(conn):
    db_pool.putconn(conn)

def init_db():
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    balance BIGINT DEFAULT 0,
                    referrals INT DEFAULT 0,
                    referrer_id BIGINT DEFAULT NULL,
                    state VARCHAR(50) DEFAULT NULL
                );
            ''')
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
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS withdraw_requests (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                    amount BIGINT,
                    card_number VARCHAR(100),
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at BIGINT
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS deposit_requests (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                    amount BIGINT,
                    file_id VARCHAR(255),
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at BIGINT
                );
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
                    type VARCHAR(30),
                    amount BIGINT,
                    created_at BIGINT
                );
            ''')
            conn.commit()
    finally:
        release_db(conn)

def log_transaction(cursor, user_id, tx_type, amount):
    cursor.execute(
        'INSERT INTO transactions (user_id, type, amount, created_at) VALUES (%s, %s, %s, %s);',
        (user_id, tx_type, amount, int(time.time()))
    )

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
                    'INSERT INTO users (user_id, balance, referrals, referrer_id) VALUES (%s, 0, 0, %s);',
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
        res = [f"{ANIMALS[key]['name']} ({count} ta)" for key, count in counts.items() if key in ANIMALS]
        return ', '.join(res) if res else 'Mavjud emas'
    finally:
        release_db(conn)

def get_main_menu(user_id=None):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('🐮 Hayvon sotib olish')
    markup.row('👤 Profil', '🔗 Referal')
    markup.row('💸 Pul kiritish', '💰 Pul yechish')
    markup.row('🌾 Mening hayvonlarim (Fermam)')
    if user_id == ADMIN_ID:
        markup.row("📋 So'rovlar")
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

def escape_md(text):
    if text is None:
        return ''
    return re.sub(r'([_*`\[\]])', r'\\\1', str(text))

@bot.message_handler(commands=['start'])
def cmd_start(message):
    args = message.text.split()
    referrer_id = args[1].replace('r', '') if len(args) > 1 and args[1].startswith('r') else None
    get_user(message.from_user.id, referrer_id)
    set_user_state(message.from_user.id, None)
    bot.send_message(
        message.chat.id,
        '🌾 *Mening Fermam botiga xush kelibsiz!*',
        reply_markup=get_main_menu(message.from_user.id),
        parse_mode='Markdown',
    )

@bot.message_handler(commands=['stats'])
def admin_stats(message):
    if message.from_user.id != ADMIN_ID:
        return

    now = int(time.time())
    day_ago = now - 86400
    week_ago = now - 7 * 86400

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # Umumiy foydalanuvchilar
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(balance), 0) FROM users;")
            total_users, total_balance = cursor.fetchone()

            # Referal orqali qo'shilganlar
            cursor.execute("SELECT COUNT(*) FROM users WHERE referrer_id IS NOT NULL;")
            total_referred = cursor.fetchone()[0]

            # Jami hayvonlar
            cursor.execute("SELECT COUNT(*) FROM user_animals;")
            total_animals = cursor.fetchone()[0]

            # Har bir hayvon turi bo'yicha sotuvlar
            cursor.execute("""
                SELECT animal_key, COUNT(*) FROM user_animals
                GROUP BY animal_key ORDER BY COUNT(*) DESC;
            """)
            animal_counts = cursor.fetchall()

            # Depozitlar
            cursor.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'pending'),
                    COUNT(*) FILTER (WHERE status = 'awaiting_check'),
                    COUNT(*) FILTER (WHERE status = 'approved'),
                    COUNT(*) FILTER (WHERE status = 'rejected'),
                    COALESCE(SUM(amount) FILTER (WHERE status = 'approved'), 0)
                FROM deposit_requests;
            """)
            dep_pending, dep_awaiting, dep_approved, dep_rejected, dep_approved_sum = cursor.fetchone()

            # Pul yechish so'rovlari
            cursor.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'pending'),
                    COUNT(*) FILTER (WHERE status = 'approved'),
                    COUNT(*) FILTER (WHERE status = 'rejected'),
                    COALESCE(SUM(amount) FILTER (WHERE status = 'approved'), 0),
                    COALESCE(SUM(amount) FILTER (WHERE status = 'pending'), 0)
                FROM withdraw_requests;
            """)
            w_pending, w_approved, w_rejected, w_approved_sum, w_pending_sum = cursor.fetchone()

            # Tranzaksiyalar bo'yicha jami harvest (yig'ilgan daromad)
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'harvest';
            """)
            total_harvested = cursor.fetchone()[0]

            # Referal bonuslari
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM transactions WHERE type = 'ref_bonus';
            """)
            ref_bonus_sum, ref_bonus_count = cursor.fetchone()

            # Admin tomonidan qo'shilgan balans
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'admin_add';
            """)
            admin_added_sum = cursor.fetchone()[0]

        conn.commit()
    finally:
        release_db(conn)

    animal_lines = []
    for key, count in animal_counts:
        name = ANIMALS.get(key, {}).get('name', key)
        animal_lines.append(f"   • {name}: {count:,} ta")
    animals_breakdown = '\n'.join(animal_lines) if animal_lines else '   • Mavjud emas'

    text = (
        f"📊 *Bot Statistikasi (to'liq):*\n\n"
        f"👥 *Foydalanuvchilar:*\n"
        f"   • Jami: {total_users:,} ta\n"
        f"   • Referal orqali qo'shilgan: {total_referred:,} ta\n\n"
        f"💰 *Balanslar:*\n"
        f"   • Foydalanuvchilardagi umumiy balans: {total_balance:,} so'm\n"
        f"   • Admin tomonidan qo'shilgan: {admin_added_sum:,} so'm\n"
        f"   • Yig'ilgan (harvest) daromad: {total_harvested:,} so'm\n"
        f"   • Referal bonuslari: {ref_bonus_sum:,} so'm ({ref_bonus_count:,} ta)\n\n"
        f"🐄 *Hayvonlar:*\n"
        f"   • Jami sotib olingan: {total_animals:,} ta\n"
        f"{animals_breakdown}\n\n"
        f"💸 *Pul kiritish (depozit) so'rovlari:*\n"
        f"   • Kutilmoqda (chek yuborilgan): {dep_pending:,} ta\n"
        f"   • Chek kutilmoqda: {dep_awaiting:,} ta\n"
        f"   • Tasdiqlangan: {dep_approved:,} ta ({dep_approved_sum:,} so'm)\n"
        f"   • Rad etilgan: {dep_rejected:,} ta\n\n"
        f"💵 *Pul yechish so'rovlari:*\n"
        f"   • Kutilmoqda: {w_pending:,} ta ({w_pending_sum:,} so'm)\n"
        f"   • Tasdiqlangan: {w_approved:,} ta ({w_approved_sum:,} so'm)\n"
        f"   • Rad etilgan: {w_rejected:,} ta"
    )

    for i in range(0, len(text), 3800):
        bot.send_message(message.chat.id, text[i:i + 3800], parse_mode='Markdown')

@bot.message_handler(commands=['add'])
def admin_add_balance(message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) < 3:
        bot.send_message(message.chat.id, "⚠️ *Xato format!*\nFoydalanish: `/add USER_ID SUMMA`\n*Masalan:* `/add 123456789 50000`", parse_mode='Markdown')
        return
    if not args[1].lstrip('-').isdigit() or not args[2].lstrip('-').isdigit():
        bot.send_message(message.chat.id, "⚠️ *USER_ID va SUMMA faqat raqamlardan iborat bo'lishi kerak!*", parse_mode='Markdown')
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
            log_transaction(cursor, target_id, 'admin_add', amount)
            conn.commit()
        bot.send_message(message.chat.id, f"✅ `{target_id}` foydalanuvchisiga *{amount:,} so'm* qo'shildi!", parse_mode='Markdown')
        try:
            bot.send_message(target_id, f"🎉 *Sizning balansingiz {amount:,} so'mga to'ldirildi!*", parse_mode='Markdown')
        except Exception:
            pass
    finally:
        release_db(conn)

def _send_pending_requests(chat_id):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, user_id, amount, card_number, created_at FROM withdraw_requests "
                "WHERE status = 'pending' ORDER BY created_at ASC;"
            )
            withdrawals = cursor.fetchall()
            cursor.execute(
                "SELECT id, user_id, amount, created_at FROM deposit_requests "
                "WHERE status = 'pending' ORDER BY created_at ASC;"
            )
            deposits = cursor.fetchall()
    finally:
        release_db(conn)

    if not withdrawals and not deposits:
        bot.send_message(chat_id, "✅ *Kutilayotgan so'rovlar yo'q.*", parse_mode='Markdown')
        return

    text = ""
    if withdrawals:
        text += "💰 *Kutilayotgan pul yechish so'rovlari:*\n\n"
        for req_id, user_id, amount, card, created_at in withdrawals:
            text += (
                f"🆔 So'rov: `{req_id}` | 👤 User: `{user_id}`\n"
                f"💵 Summa: *{amount:,} so'm* | 💳 Karta: `{escape_md(card)}`\n"
                f"/approve_w_{req_id} yoki /reject_w_{req_id}\n\n"
            )
    if deposits:
        text += "💸 *Kutilayotgan pul kiritish so'rovlari:*\n\n"
        for req_id, user_id, amount, created_at in deposits:
            text += (
                f"🆔 So'rov: `{req_id}` | 👤 User: `{user_id}`\n"
                f"💵 Da'vo qilingan summa: *{amount:,} so'm*\n"
                f"/approve_d_{req_id} yoki /reject_d_{req_id}\n\n"
            )
    for i in range(0, len(text), 3800):
        bot.send_message(chat_id, text[i:i + 3800], parse_mode='Markdown')

@bot.message_handler(commands=['pending'])
def show_pending_requests(message):
    if message.from_user.id != ADMIN_ID:
        return
    _send_pending_requests(message.chat.id)

@bot.message_handler(func=lambda msg: msg.text == "📋 So'rovlar")
def pending_button_handler(message):
    if message.from_user.id != ADMIN_ID:
        return
    _send_pending_requests(message.chat.id)

def _approve_withdraw_by_id(request_id, admin_chat_id, notify_admin=True):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE withdraw_requests SET status = 'approved' WHERE id = %s AND status = 'pending' RETURNING user_id, amount;",
                (request_id,)
            )
            row = cursor.fetchone()
            if not row:
                if notify_admin:
                    bot.send_message(admin_chat_id, "⚠️ Bu so'rov topilmadi yoki allaqachon ko'rib chiqilgan.")
                return None
            user_id, amount = row
            conn.commit()
    finally:
        release_db(conn)

    if notify_admin:
        bot.send_message(admin_chat_id, f"✅ So'rov #{request_id} tasdiqlandi ({amount:,} so'm, user {user_id}).")
    try:
        bot.send_message(user_id, f"✅ *Sizning {amount:,} so'm pul yechish so'rovingiz tasdiqlandi va kartangizga o'tkazildi!*", parse_mode='Markdown')
    except Exception:
        pass
    return user_id, amount

def _reject_withdraw_by_id(request_id, admin_chat_id, notify_admin=True):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE withdraw_requests SET status = 'rejected' WHERE id = %s AND status = 'pending' RETURNING user_id, amount;",
                (request_id,)
            )
            row = cursor.fetchone()
            if not row:
                if notify_admin:
                    bot.send_message(admin_chat_id, "⚠️ Bu so'rov topilmadi yoki allaqachon ko'rib chiqilgan.")
                return None
            user_id, amount = row
            cursor.execute('UPDATE users SET balance = balance + %s WHERE user_id = %s;', (amount, user_id))
            log_transaction(cursor, user_id, 'withdraw_reject_refund', amount)
            conn.commit()
    finally:
        release_db(conn)

    if notify_admin:
        bot.send_message(admin_chat_id, f"❌ So'rov #{request_id} rad etildi, balans qaytarildi ({amount:,} so'm, user {user_id}).")
    try:
        bot.send_message(user_id, f"❌ *Sizning {amount:,} so'm pul yechish so'rovingiz rad etildi.* Mablag' balansingizga qaytarildi.", parse_mode='Markdown')
    except Exception:
        pass
    return user_id, amount

def _approve_deposit_by_id(request_id, admin_chat_id, notify_admin=True):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE deposit_requests SET status = 'approved' WHERE id = %s AND status = 'pending' RETURNING user_id, amount;",
                (request_id,)
            )
            row = cursor.fetchone()
            if not row:
                if notify_admin:
                    bot.send_message(admin_chat_id, "⚠️ Bu so'rov topilmadi yoki allaqachon ko'rib chiqilgan.")
                return None
            user_id, amount = row
            cursor.execute('UPDATE users SET balance = balance + %s WHERE user_id = %s;', (amount, user_id))
            log_transaction(cursor, user_id, 'deposit_approved', amount)
            conn.commit()
    finally:
        release_db(conn)

    if notify_admin:
        bot.send_message(admin_chat_id, f"✅ Deposit #{request_id} tasdiqlandi ({amount:,} so'm, user {user_id}).")
    try:
        bot.send_message(user_id, f"✅ *Sizning {amount:,} so'mlik to'lovingiz tasdiqlandi va balansingizga qo'shildi!*", parse_mode='Markdown')
    except Exception:
        pass
    return user_id, amount

def _reject_deposit_by_id(request_id, admin_chat_id, notify_admin=True):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE deposit_requests SET status = 'rejected' WHERE id = %s AND status = 'pending' RETURNING user_id, amount;",
                (request_id,)
            )
            row = cursor.fetchone()
            if not row:
                if notify_admin:
                    bot.send_message(admin_chat_id, "⚠️ Bu so'rov topilmadi yoki allaqachon ko'rib chiqilgan.")
                return None
            user_id, amount = row
            conn.commit()
    finally:
        release_db(conn)

    if notify_admin:
        bot.send_message(admin_chat_id, f"❌ Deposit #{request_id} rad etildi ({amount:,} so'm, user {user_id}).")
    try:
        bot.send_message(user_id, f"❌ *Sizning {amount:,} so'mlik to'lov so'rovingiz rad etildi.* Savol bo'lsa admin bilan bog'laning.", parse_mode='Markdown')
    except Exception:
        pass
    return user_id, amount

@bot.message_handler(commands=['approve_w'])
def approve_withdraw_cmd(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split('_')
    if len(parts) < 3 or not parts[2].isdigit():
        return
    _approve_withdraw_by_id(int(parts[2]), message.chat.id)

@bot.message_handler(commands=['reject_w'])
def reject_withdraw_cmd(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split('_')
    if len(parts) < 3 or not parts[2].isdigit():
        return
    _reject_withdraw_by_id(int(parts[2]), message.chat.id)

@bot.message_handler(commands=['approve_d'])
def approve_deposit_cmd(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split('_')
    if len(parts) < 3 or not parts[2].isdigit():
        return
    _approve_deposit_by_id(int(parts[2]), message.chat.id)

@bot.message_handler(commands=['reject_d'])
def reject_deposit_cmd(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split('_')
    if len(parts) < 3 or not parts[2].isdigit():
        return
    _reject_deposit_by_id(int(parts[2]), message.chat.id)

@bot.message_handler(func=lambda msg: msg.text == '⬅️ Ortga qaytish')
def back_to_main_menu(message):
    set_user_state(message.from_user.id, None)
    bot.send_message(message.chat.id, '▪️ *Bosh sahifaga xush kelibsiz.*', reply_markup=get_main_menu(message.from_user.id), parse_mode='Markdown')

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
    card_digits = re.sub(r'\s+', '', card)
    if not card_digits.isdigit() or not (12 <= len(card_digits) <= 19):
        bot.send_message(message.chat.id, "⚠️ *Karta raqami noto'g'ri!* Faqat raqamlardan iborat bo'lishi kerak.", parse_mode='Markdown')
        return
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
            cursor.execute(
                'INSERT INTO withdraw_requests (user_id, amount, card_number, created_at) VALUES (%s, %s, %s, %s) RETURNING id;',
                (user_id, amount, card_digits, int(time.time()))
            )
            request_id = cursor.fetchone()[0]
            log_transaction(cursor, user_id, 'withdraw_hold', -amount)
            conn.commit()
    finally:
        release_db(conn)

    set_user_state(user_id, None)
    bot.send_message(message.chat.id, "✅ *Arizangiz qabul qilindi!* Admin tez orada to'lovni amalga oshiradi.", reply_markup=get_main_menu(user_id), parse_mode='Markdown')
    try:
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_w_{request_id}"),
            types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_w_{request_id}")
        )
        bot.send_message(
            ADMIN_ID,
            f"💸 *Yangi pul yechish so'rovi!* (ID: {request_id})\n\n👤 ID: `{user_id}`\n💰 Summa: *{amount:,} so'm*\n💳 Karta: `{escape_md(card_digits)}`",
            parse_mode='Markdown',
            reply_markup=markup
        )
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_w_'))
def approve_withdraw(call):
    if call.from_user.id != ADMIN_ID:
        return
    request_id = int(call.data.split('_')[2])
    result = _approve_withdraw_by_id(request_id, call.message.chat.id, notify_admin=False)
    if result is None:
        bot.answer_callback_query(call.id, "⚠️ Bu so'rov allaqachon ko'rib chiqilgan!", show_alert=True)
        return
    bot.edit_message_text(
        f"{call.message.text}\n\n✅ *STATUS: ADMIN TARAFIDAN TO'LANDI*",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_w_'))
def reject_withdraw(call):
    if call.from_user.id != ADMIN_ID:
        return
    request_id = int(call.data.split('_')[2])
    result = _reject_withdraw_by_id(request_id, call.message.chat.id, notify_admin=False)
    if result is None:
        bot.answer_callback_query(call.id, "⚠️ Bu so'rov allaqachon ko'rib chiqilgan!", show_alert=True)
        return
    bot.edit_message_text(
        f"{call.message.text}\n\n❌ *STATUS: RAD ETILDI (Balans qaytarildi)*",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )

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
            if key not in ANIMALS:
                continue
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
                if key not in ANIMALS:
                    continue
                max_duration = 30 * 86400
                active_time = min(now, buy_time + max_duration)
                if active_time > last_harvest:
                    earned = int((active_time - last_harvest) * (ANIMALS[key]['daily'] / 86400))
                    total_uncollected += earned
                    cursor.execute('UPDATE user_animals SET last_harvest = %s WHERE id = %s;', (active_time, a_id))

            if total_uncollected > 0:
                cursor.execute('UPDATE users SET balance = balance + %s WHERE user_id = %s;', (total_uncollected, user_id))
                log_transaction(cursor, user_id, 'harvest', total_uncollected)
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
    set_user_state(message.from_user.id, 'waiting_for_deposit_amount')
    text = (
        f"💸 *Quyidagi kartalardan biriga to'lov qiling:*\n\n"
        f"💳 `{CARD_NUMBER_1}`\n"
        f"💳 `{CARD_NUMBER_2}`\n"
        f"👤 Karta egasi: *{CARD_OWNER}*\n\n"
        f"Iltimos, avval to'lov qilmoqchi bo'lgan summangizni kiriting (faqat raqam, masalan: `50000`)."
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('⬅️ Ortga qaytish')
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda msg: get_user_state(msg.from_user.id) == 'waiting_for_deposit_amount')
def handle_deposit_amount(message):
    text = message.text.strip() if message.text else ''
    if not text.isdigit() or int(text) <= 0:
        bot.send_message(message.chat.id, "⚠️ *Iltimos, faqat musbat raqam kiriting.* Masalan: `50000`", parse_mode='Markdown')
        return

    amount = int(text)
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO deposit_requests (user_id, amount, status, created_at) VALUES (%s, %s, %s, %s) RETURNING id;',
                (message.from_user.id, amount, 'awaiting_check', int(time.time()))
            )
            request_id = cursor.fetchone()[0]
            conn.commit()
    finally:
        release_db(conn)

    set_user_state(message.from_user.id, f'waiting_for_check_{request_id}')
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('⬅️ Ortga qaytish')
    bot.send_message(message.chat.id, "📷 *Endi to'lov chekini (rasm yoki fayl) yuboring.*", parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(content_types=['photo', 'document'],
                      func=lambda msg: (get_user_state(msg.from_user.id) or '').startswith('waiting_for_check_'))
def handle_check_upload(message):
    state = get_user_state(message.from_user.id)
    request_id = int(state.split('_')[-1])
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE deposit_requests SET file_id = %s, status = 'pending' WHERE id = %s RETURNING amount;",
                (file_id, request_id)
            )
            row = cursor.fetchone()
            amount = row[0] if row else 0
            conn.commit()
    finally:
        release_db(conn)

    set_user_state(message.from_user.id, None)
    bot.send_message(message.chat.id, "✅ *Chek qabul qilindi.* Admin tez orada tasdiqlaydi.", reply_markup=get_main_menu(message.from_user.id), parse_mode='Markdown')
    try:
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_d_{request_id}"),
            types.InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_d_{request_id}")
        )
        caption = f"💸 *Yangi to'lov cheki!* (ID: {request_id})\n\n👤 ID: `{message.from_user.id}`\n💰 Da'vo qilingan summa: *{amount:,} so'm*"
        if message.photo:
            bot.send_photo(ADMIN_ID, file_id, caption=caption, parse_mode='Markdown', reply_markup=markup)
        else:
            bot.send_document(ADMIN_ID, file_id, caption=caption, parse_mode='Markdown', reply_markup=markup)
    except Exception:
        pass

@bot.message_handler(func=lambda msg: (get_user_state(msg.from_user.id) or '').startswith('waiting_for_check_'))
def handle_check_wrong_type(message):
    bot.send_message(message.chat.id, "⚠️ *Iltimos, chekni rasm yoki fayl sifatida yuboring.*", parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_d_'))
def approve_deposit(call):
    if call.from_user.id != ADMIN_ID:
        return
    request_id = int(call.data.split('_')[2])
    result = _approve_deposit_by_id(request_id, call.message.chat.id, notify_admin=False)
    if result is None:
        bot.answer_callback_query(call.id, "⚠️ Bu so'rov allaqachon ko'rib chiqilgan!", show_alert=True)
        return
    try:
        bot.edit_message_caption(f"{call.message.caption}\n\n✅ *STATUS: TASDIQLANDI*", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_d_'))
def reject_deposit(call):
    if call.from_user.id != ADMIN_ID:
        return
    request_id = int(call.data.split('_')[2])
    result = _reject_deposit_by_id(request_id, call.message.chat.id, notify_admin=False)
    if result is None:
        bot.answer_callback_query(call.id, "⚠️ Bu so'rov allaqachon ko'rib chiqilgan!", show_alert=True)
        return
    try:
        bot.edit_message_caption(f"{call.message.caption}\n\n❌ *STATUS: RAD ETILDI*", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    except Exception:
        pass

@bot.message_handler(func=lambda msg: msg.text == '🐮 Hayvon sotib olish')
def show_shop(message):
    bot.send_message(message.chat.id, '🛒 *Hayvonni tanlang:*', reply_markup=get_shop_inline(), parse_mode='Markdown')

# --- YANGILANGAN VIEW_ANIMAL FUNKSIYASI ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('view_'))
def view_animal(call):
    key = call.data.split('_')[1]
    if key not in ANIMALS:
        return
    item = ANIMALS[key]

    text = (
        f"Nomi: {item['name']}\n\n"
        f"▫️ Narxi: {item['price']:,} so'm\n"
        f"▫️ Kunlik daromad: {item['daily']:,} so'm\n"
        f"▫️ Jami daromad (30 kun): {item['total']:,} so'm\n"
        f"▫️ Ishlash muddati: 30 kun"
    )

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
    if key not in ANIMALS:
        return
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
            log_transaction(cursor, user_id, f'buy_{key}', -item['price'])

            cursor.execute('SELECT referrer_id FROM users WHERE user_id = %s;', (user_id,))
            ref_row = cursor.fetchone()
            if ref_row and ref_row[0]:
                ref_id = ref_row[0]
                bonus = int(item['price'] * 0.10)
                cursor.execute('UPDATE users SET balance = balance + %s WHERE user_id = %s;', (bonus, ref_id))
                log_transaction(cursor, ref_id, 'ref_bonus', bonus)

            conn.commit()
    finally:
        release_db(conn)

    bot.answer_callback_query(call.id, f"✅ {item['name']} sotib olindi!", show_alert=True)
    bot.send_message(call.message.chat.id, f"🎉 *Tabriklaymiz! {item['name']} sotib olindi!*", parse_mode='Markdown')

if __name__ == '__main__':
    init_db()

    try:
        bot.remove_webhook()
    except Exception as e:
        print(f'remove_webhook xatosi: {e}')

    time.sleep(2)
    print('Bot tayyor va ishga tushdi!')

    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            print(f'Polling xatosi, 5 soniyadan keyin qayta urinadi: {e}')
            time.sleep(5)
