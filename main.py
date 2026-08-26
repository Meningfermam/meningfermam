
import os
import time
import random
import telebot
from telebot import types
import psycopg2
from psycopg2.extras import RealDictCursor

# Render'dagi Environment Variable'dan olinadi
DATABASE_URL = os.environ.get('DATABASE_URL')

API_TOKEN = '8802630482:AAE7ev5RYWN3YfwWYhxbV855XiJy3MqF7Yw'
BOT_USERNAME = 'Meningfeermam_bot'
bot = telebot.TeleBot(API_TOKEN)

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
user_states = {}


def get_db_connection():
    """PostgreSQL bazasiga ulanish yaratish"""
    return psycopg2.connect(DATABASE_URL, sslmode='require')


def init_db():
    """PostgreSQL jadvallarini yaratish"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    balance BIGINT DEFAULT 0,
                    referrals INT DEFAULT 0,
                    referrer_id BIGINT DEFAULT NULL,
                    last_bonus BIGINT DEFAULT 0
                );
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


def get_user(user_id, referrer_id=None):
    with get_db_connection() as conn:
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
                    cursor.execute(
                        'UPDATE users SET referrals = referrals + 1 WHERE user_id = %s;',
                        (ref_id,)
                    )
                    try:
                        bot.send_message(
                            ref_id,
                            "🎉 *Sizning referal havolangiz orqali yangi foydalanuvchi botga qo'shildi!*\nU hayvon sotib olganda sizga 10% bonus beriladi 💸",
                            parse_mode='Markdown'
                        )
                    except Exception:
                        pass

                conn.commit()
                user = (0, 0)
            return user


def get_user_animals_summary(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT animal_key FROM user_animals WHERE user_id = %s;', (user_id,))
            rows = cursor.fetchall()

    if not rows:
        return 'Mavjud emas'

    counts = {}
    for r in rows:
        key = r[0]
        counts[key] = counts.get(key, 0) + 1

    res = []
    for key, count in counts.items():
        res.append(f"{ANIMALS[key]['name']} ({count} ta)")
    return ', '.join(res)


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


@bot.message_handler(commands=['balance'])
def admin_change_balance(message):
    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split()
    if len(args) < 3:
        bot.send_message(message.chat.id, "⚠️ Xato format! Ishlatilishi:\n`/balance [user_id] [summa]`", parse_mode='Markdown')
        return

    try:
        target_user_id = int(args[1])
        amount = int(args[2])
    except ValueError:
        bot.send_message(message.chat.id, "❌ ID va summa faqat raqamlardan iborat bo'lishi kerak!")
        return

    get_user(target_user_id)

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET balance = balance + %s WHERE user_id = %s;", (amount, target_user_id))
            conn.commit()
            cursor.execute("SELECT balance FROM users WHERE user_id = %s;", (target_user_id,))
            new_balance = cursor.fetchone()[0]

    bot.send_message(
        message.chat.id,
        f"✅ Muvaffaqiyatli o'zgartirildi!\n👤 Foydalanuvchi ID: `{target_user_id}`\n💰 Summa: {amount:,} so'm\n💳 Yangi balansi: *{new_balance:,} so'm*",
        parse_mode='Markdown'
    )

    try:
        if amount > 0:
            bot.send_message(target_user_id, f"🎉 *Admin tomonidan balansingizga {amount:,} so'm qo'shildi!*", parse_mode='Markdown')
        else:
            bot.send_message(target_user_id, f"⚠️ *Admin tomonidan balansingizdan {abs(amount):,} so'm ayirildi.*", parse_mode='Markdown')
    except Exception:
        pass


@bot.message_handler(commands=['start'])
def cmd_start(message):
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith('r'):
        referrer_id = args[1].replace('r', '')

    get_user(message.from_user.id, referrer_id)
    bot.send_message(
        message.chat.id,
        '🌾 *Mening Fermam botiga xush kelibsiz!*\n\nQuyidagi menyulardan foydalanishingiz mumkin:',
        reply_markup=get_main_menu(),
        parse_mode='Markdown',
    )


@bot.message_handler(func=lambda msg: msg.text == '🎁 Kunlik bonus')
def daily_bonus_handler(message):
    user_id = message.from_user.id
    get_user(user_id)

    now = int(time.time())
    cooldown = 24 * 60 * 60

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT last_bonus FROM users WHERE user_id = %s;', (user_id,))
            last_bonus = cursor.fetchone()[0]

            if now - last_bonus < cooldown:
                remaining_time = cooldown - (now - last_bonus)
                hours = remaining_time // 3600
                minutes = (remaining_time % 3600) // 60
                bot.send_message(
                    message.chat.id,
                    f"⏳ *Siz allaqachon kunlik bonusni olgansiz!*\n\nKeyingi vaqt: *{hours} soat {minutes} daqiqa*dan keyin 🕒",
                    parse_mode='Markdown'
                )
                return

            bonus_amount = random.randint(500, 5000)
            cursor.execute('UPDATE users SET balance = balance + %s, last_bonus = %s WHERE user_id = %s;', (bonus_amount, now, user_id))
            conn.commit()

    bot.send_message(
        message.chat.id,
        f"🎁 *Tabriklaymiz! Siz kunlik bonusni oldingiz.*\n\n💰 Balansingizga *{bonus_amount:,} so'm* qo'shildi! ✨",
        parse_mode='Markdown'
    )


@bot.message_handler(func=lambda msg: msg.text == '🌾 Mening hayvonlarim (Fermam)')
def show_farm(message):
    user_id = message.from_user.id
    now = int(time.time())

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT id, animal_key, buy_time, last_harvest FROM user_animals WHERE user_id = %s;', (user_id,))
            animals = cursor.fetchall()

    if not animals:
        bot.send_message(
            message.chat.id,
            "🌾 *Sizda hali hech qanday hayvon yo'q.*\n\nHayvon sotib olish uchun '🐮 Hayvon sotib olish' bo'limiga o'ting.",
            parse_mode='Markdown',
        )
        return

    total_uncollected = 0
    farm_details = []

    for a_id, key, buy_time, last_harvest in animals:
        max_duration = 30 * 86400
        active_time = min(now, buy_time + max_duration)

        if active_time > last_harvest:
            seconds_passed = active_time - last_harvest
            daily_income = ANIMALS[key]['daily']
            income_per_second = daily_income / 86400
            earned = int(seconds_passed * income_per_second)
            total_uncollected += earned

        farm_details.append(f"• {ANIMALS[key]['name']}")

    text = (
        f"🌾 *Sizning fermangiz:*\n\n📋 *Mavjud hayvonlar:*\n"
        + '\n'.join(farm_details)
        + f"\n\n💰 *Yig'ilgan daromad:* {total_uncollected:,} so'm\n\nDaromadni balansingizga o'tkazish uchun tugmani bosing 👇"
    )

    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("📥 Daromadni yig'ish", callback_data='collect_income'))
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'collect_income')
def collect_income(call):
    user_id = call.from_user.id
    now = int(time.time())

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT id, animal_key, buy_time, last_harvest FROM user_animals WHERE user_id = %s;', (user_id,))
            animals = cursor.fetchall()

            total_uncollected = 0

            for a_id, key, buy_time, last_harvest in animals:
                max_duration = 30 * 86400
                active_time = min(now, buy_time + max_duration)

                if active_time > last_harvest:
                    seconds_passed = active_time - last_harvest
                    daily_income = ANIMALS[key]['daily']
                    income_per_second = daily_income / 86400
                    earned = int(seconds_passed * income_per_second)
                    total_uncollected += earned
                    cursor.execute('UPDATE user_animals SET last_harvest = %s WHERE id = %s;', (active_time, a_id))

            if total_uncollected > 0:
                cursor.execute('UPDATE users SET balance = balance + %s WHERE user_id = %s;', (total_uncollected, user_id))
                conn.commit()
                bot.answer_callback_query(call.id, f"✅ {total_uncollected:,} so'm balansingizga qo'shildi!", show_alert=True)
                bot.edit_message_text(
                    f"🎉 *Barcha daromadlar yig'ib olindi!*\n\nBalansga o'tkazildi: *{total_uncollected:,} so'm*",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
            else:
                bot.answer_callback_query(call.id, "⚠️ Hozircha yig'ish uchun daromad yo'q!", show_alert=True)


@bot.message_handler(func=lambda msg: msg.text == '👤 Profil')
def show_profile(message):
    u = get_user(message.from_user.id)
    animals_text = get_user_animals_summary(message.from_user.id)

    text = (
        f"👤 *Sizning shaxsiy kabinetingiz:*\n\n"
        f"🆔 *ID raqamingiz:* `{message.from_user.id}`\n"
        f"💰 *Asosiy balansingiz:* {u[0]:,} so'm\n"
        f"👥 *Taklif qilgan do'stlaringiz:* {u[1]} ta\n"
        f"🌾 *Fermangizdagi hayvonlar:* {animals_text}"
    )
    bot.send_message(message.chat.id, text, parse_mode='Markdown')


@bot.message_handler(func=lambda msg: msg.text == '🔗 Referal')
def show_ref(message):
    ref_link = f'https://t.me/{BOT_USERNAME}?start=r{message.from_user.id}'
    text = (
        f"Do'stingizni taklif qilish orqali daromad oling!\n\n"
        f"Sizning referal havolangiz:\n{ref_link}"
    )
    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda msg: msg.text == '💸 Pul kiritish')
def deposit_start(message):
    text = (
        f"💸 *Hisobingizni to'ldirmoqchi bo'lsangiz, quyidagi kartaga to'lov qiling.*\n\n"
        f"💳 *Karta:* `{CARD_NUMBER}`\n\n"
        f"👤 To'lov qilgandan so'ng *'✅ To'lovni amalga oshirdim'* tugmasini bosing va chekni yuboring."
    )
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("✅ To'lovni amalga oshirdim", callback_data='pay_done'))
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'pay_done')
def pay_done_callback(call):
    user_states[call.from_user.id] = 'waiting_for_check'
    text = "👨‍💼 *To'lov kvitansiyasi (chekini) yuboring.*"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('⬅️ Ortga qaytish')
    bot.send_message(call.message.chat.id, text, parse_mode='Markdown', reply_markup=markup)


@bot.message_handler(func=lambda msg: msg.text == '⬅️ Ortga qaytish')
def back_to_main_menu(message):
    user_states.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, '▪️ *Bosh sahifaga xush kelibsiz.*', reply_markup=get_main_menu(), parse_mode='Markdown')


@bot.message_handler(content_types=['photo', 'document'], func=lambda msg: user_states.get(msg.from_user.id) == 'waiting_for_check')
def handle_check_upload(message):
    user_states.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "✅ *Chekingiz qabul qilindi.*", reply_markup=get_main_menu(), parse_mode='Markdown')
    if message.photo:
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"ID: `{message.from_user.id}`")


@bot.message_handler(func=lambda msg: msg.text == '🐮 Hayvon sotib olish')
def show_shop(message):
    bot.send_message(message.chat.id, '🛒 *Xarid qilish uchun hayvonni tanlang:*', reply_markup=get_shop_inline(), parse_mode='Markdown')


@bot.callback_query_handler(func=lambda call: call.data.startswith('view_'))
def view_animal(call):
    key = call.data.split('_')[1]
    item = ANIMALS[key]
    text = (
        f"Hayvon nomi: {item['name']}\n\n"
        f"▫️ Narxi: {item['price']:,} so'm\n"
        f"▫️ Kunlik daromad: {item['daily']:,} so'm\n"
        f"▫️ Umumiy daromad: {item['total']:,} so'm\n"
    )
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton('💸 Sotib olish', callback_data=f'buy_{key}'))
    markup.row(types.InlineKeyboardButton('⬅️ Orqaga', callback_data='back_to_shop'))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')


@bot.callback_query_handler(func=lambda call: call.data == 'back_to_shop')
def back_shop(call):
    bot.edit_message_text('🛒 *Xarid qilish uchun hayvonni tanlang:*', call.message.chat.id, call.message.message_id, reply_markup=get_shop_inline(), parse_mode='Markdown')


@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def buy_animal(call):
    key = call.data.split('_')[1]
    user_id = call.from_user.id
    u = get_user(user_id)
    item = ANIMALS[key]

    if u[0] < item['price']:
        bot.answer_callback_query(call.id, '❌ Balans yetarli emas!', show_alert=True)
        return

    now = int(time.time())
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('UPDATE users SET balance = balance - %s WHERE user_id = %s;', (item['price'], user_id))
            cursor.execute('INSERT INTO user_animals (user_id, animal_key, buy_time, last_harvest) VALUES (%s, %s, %s, %s);', (user_id, key, now, now))

            cursor.execute('SELECT referrer_id FROM users WHERE user_id = %s;', (user_id,))
            ref_row = cursor.fetchone()
            if ref_row and ref_row[0]:
                ref_id = ref_row[0]
                bonus = int(item['price'] * 0.10)
                cursor.execute('UPDATE users SET balance = balance + %s WHERE user_id = %s;', (bonus, ref_id))
                try:
                    bot.send_message(ref_id, f"🎉 *Do'stingiz hayvon sotib oldi!* Sizga *{bonus:,} so'm* bonus berildi!", parse_mode='Markdown')
                except Exception:
                    pass
            conn.commit()

    bot.answer_callback_query(call.id, f"✅ {item['name']} sotib olindi!", show_alert=True)
    bot.send_message(call.message.chat.id, f"🎉 *Tabriklaymiz! Siz {item['name']} sotib oldingiz!*", parse_mode='Markdown')


if __name__ == '__main__':
    init_db()
    print('Mening Fermam Bot muvaffaqiyatli ishga tushdi!')
    bot.infinity_polling()
