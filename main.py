import os
import sqlite3
import threading
import time
from flask import Flask
import telebot
from telebot import types

API_TOKEN = '8802630482:AAG-_S2mNc2f5E8VbNz3XepoPLSzNEzVBSQ'
BOT_USERNAME = 'Meningfeermam_bot'
bot = telebot.TeleBot(API_TOKEN)

# Render uchun kichik veb-server (Port xatoligining oldini olish uchun)
app = Flask(__name__)


@app.route('/')
def home():
  return 'Bot is running!'


def run_web():
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port)


# SKRINSHOTLARDAGI ANIQ HAYVONLAR VA DAROMADLAR
ANIMALS = {
    'tovuq': {
        'name': '🐔 Tovuq',
        'price': 24000,
        'daily': 2400,
        'total': 72000,
    },
    'quyon': {
        'name': '🐇 Quyon',
        'price': 45000,
        'daily': 4500,
        'total': 135000,
    },
    'goz': {
        'name': "🪿 G'oz",
        'price': 115000,
        'daily': 12000,
        'total': 360000,
    },
    'echki': {
        'name': '🐐 Echki',
        'price': 200000,
        'daily': 25000,
        'total': 750000,
    },
    'qoy': {
        'name': "🐑 Qo'y",
        'price': 325000,
        'daily': 3750,
        'total': 1125000,
    },
    'sigir': {
        'name': '🐄 Sigir',
        'price': 450000,
        'daily': 50000,
        'total': 1500000,
    },
    'ot': {
        'name': '🐎 Ot',
        'price': 1200000,
        'daily': 150000,
        'total': 4500000,
    },
    'tuya': {
        'name': '🐪 Tuya',
        'price': 2400000,
        'daily': 300000,
        'total': 9000000,
    },
    'buqa': {
        'name': '🐂 Buqa',
        'price': 3600000,
        'daily': 425000,
        'total': 12750000,
    },
}

ADMIN_ID = 925576047
CARD_NUMBER = '9860080311226940'
user_states = {}

DB_NAME = 'farm_data.db'


def init_db():
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            referrer_id INTEGER DEFAULT NULL
        )
    ''')
  cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_animals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            animal_key TEXT,
            buy_time INTEGER,
            last_harvest INTEGER
        )
    ''')
  conn.commit()
  conn.close()


def get_user(user_id, referrer_id=None):
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute(
      'SELECT balance, referrals FROM users WHERE user_id = ?', (user_id,)
  )
  user = cursor.fetchone()

  if not user:
    ref_id = None
    if referrer_id and str(referrer_id).isdigit():
      ref_id = int(referrer_id)
      if ref_id == user_id:
        ref_id = None

    cursor.execute(
        'INSERT INTO users (user_id, balance, referrals, referrer_id) VALUES'
        ' (?, 0, 0, ?)',
        (user_id, ref_id),
    )

    if ref_id:
      cursor.execute(
          'UPDATE users SET referrals = referrals + 1 WHERE user_id = ?',
          (ref_id,),
      )
      try:
        bot.send_message(
            ref_id,
            '🎉 **Sizning referal havolangiz orqali yangi foydalanuvchi botga'
            " qo'shildi!**\nU hayvon sotib olganda sizga 10% bonus beriladi 💸",
            parse_mode='Markdown',
        )
      except:
        pass

    conn.commit()
    user = (0, 0)
  conn.close()
  return user


def get_user_animals_summary(user_id):
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute(
      'SELECT animal_key FROM user_animals WHERE user_id = ?', (user_id,)
  )
  rows = cursor.fetchall()
  conn.close()

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


# MENYULAR
def get_main_menu():
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
  markup.row('🐮 Hayvon sotib olish')
  markup.row('👤 Profil', '🔗 Referal')
  markup.row('💸 Pul kiritish', '💰 Pul yechish')
  markup.row('🌾 Mening hayvonlarim (Fermam)')
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


# ASOSIY HANDLERLAR
@bot.message_handler(commands=['start'])
def cmd_start(message):
  args = message.text.split()
  referrer_id = None
  if len(args) > 1 and args[1].startswith('r'):
    referrer_id = args[1].replace('r', '')

  get_user(message.from_user.id, referrer_id)
  bot.send_message(
      message.chat.id,
      '🌾 **Mening Fermam botiga xush kelibsiz!**\n\nQuyidagi menyulardan'
      ' foydalanishingiz mumkin:',
      reply_markup=get_main_menu(),
      parse_mode='Markdown',
  )


# ADMIN BALANSni O'ZGARTIRISH BUYRUG'I
@bot.message_handler(commands=['balance'])
def admin_change_balance(message):
  if message.from_user.id != ADMIN_ID:
    return

  args = message.text.split()
  if len(args) < 3:
    bot.send_message(
        message.chat.id,
        "⚠️ Xato format!\nIshlatish: `/balance [user_id] [miqdor]`\nMisol:"
        " `/balance 123456789 50000` (pul qo'shish) yoki `/balance 123456789"
        " -20000` (pul ayirish)",
        parse_mode='Markdown',
    )
    return

  target_user_id = args[1]
  try:
    amount = int(args[2])
  except ValueError:
    bot.send_message(message.chat.id, "⚠️ Miqdor raqam bo'lishi kerak!")
    return

  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute('SELECT balance FROM users WHERE user_id = ?', (target_user_id,))
  user = cursor.fetchone()

  if not user:
    conn.close()
    bot.send_message(
        message.chat.id, '❌ Bu ID raqamdagi foydalanuvchi bazadan topilmadi.'
    )
    return

  cursor.execute(
      'UPDATE users SET balance = balance + ? WHERE user_id = ?',
      (amount, target_user_id),
  )
  conn.commit()

  cursor.execute(
      'SELECT balance FROM users WHERE user_id = ?', (target_user_id,)
  )
  new_balance = cursor.fetchone()[0]
  conn.close()

  bot.send_message(
      message.chat.id,
      f'✅ Muvaffaqiyatli bajarildi!\nFoydalanuvchi ID: `{target_user_id}`\nJoriy'
      f' balansi: **{new_balance:,} so\'m**',
      parse_mode='Markdown',
  )

  try:
    if amount > 0:
      bot.send_message(
          target_user_id,
          f"🎉 Admin tomonidan balansingizga **{amount:,} so'm** qo'shildi! 💳",
          parse_mode='Markdown',
      )
    else:
      bot.send_message(
          target_user_id,
          f"⚠️ Admin tomonidan balansingizdan **{abs(amount):,} so'm**"
          ' yechib olindi.',
          parse_mode='Markdown',
      )
  except:
    pass


@bot.message_handler(func=lambda msg: msg.text == '🌾 Mening hayvonlarim (Fermam)')
def show_farm(message):
  user_id = message.from_user.id
  now = int(time.time())

  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute(
      'SELECT id, animal_key, buy_time, last_harvest FROM user_animals WHERE'
      ' user_id = ?',
      (user_id,),
  )
  animals = cursor.fetchall()

  if not animals:
    conn.close()
    bot.send_message(
        message.chat.id,
        "🌾 **Sizda hali hech qanday hayvon yo'q.**\n\nHayvon sotib olish uchun"
        " '🐮 Hayvon sotib olish' bo'limiga o'ting.",
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

  conn.close()

  text = (
      f'🌾 **Sizning fermangiz:**\n\n📋 **Mavjud hayvonlar:**\n'
      + '\n'.join(farm_details)
      + f"\n\n💰 **Yig'ilgan va olmagan daromadingiz:** {total_uncollected:,}"
      f" so'm\n\nDaromadni balansingizga o'tkazish uchun quyidagi tugmani"
      ' bosing 👇'
  )

  markup = types.InlineKeyboardMarkup()
  markup.row(
      types.InlineKeyboardButton(
          "📥 Daromadni yig'ish", callback_data='collect_income'
      )
  )
  bot.send_message(
      message.chat.id, text, parse_mode='Markdown', reply_markup=markup
  )


@bot.callback_query_handler(func=lambda call: call.data == 'collect_income')
def collect_income(call):
  user_id = call.from_user.id
  now = int(time.time())

  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  cursor.execute(
      'SELECT id, animal_key, buy_time, last_harvest FROM user_animals WHERE'
      ' user_id = ?',
      (user_id,),
  )
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
      cursor.execute(
          'UPDATE user_animals SET last_harvest = ? WHERE id = ?',
          (active_time, a_id),
      )

  if total_uncollected > 0:
    cursor.execute(
        'UPDATE users SET balance = balance + ? WHERE user_id = ?',
        (total_uncollected, user_id),
    )
    conn.commit()
    conn.close()
    bot.answer_callback_query(
        call.id,
        f"✅ {total_uncollected:,} so'm balansingizga qo'shildi!",
        show_alert=True,
    )
    bot.edit_message_text(
        f'🎉 **Barcha daromadlar yig\'ib olindi!**\n\nBalansga o\'tkazildi:'
        f' **{total_uncollected:,} so\'m**',
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown',
    )
  else:
    conn.close()
    bot.answer_callback_query(
        call.id, "⚠️ Hozircha yig'ish uchun daromad yo'q!", show_alert=True
    )


@bot.message_handler(func=lambda msg: msg.text == '👤 Profil')
def show_profile(message):
  u = get_user(message.from_user.id)
  animals_text = get_user_animals_summary(message.from_user.id)

  text = (
      f'👤 **Sizning shaxsiy kabinetingiz:**\n\n🆔 **ID raqamingiz:**'
      f' `{message.from_user.id}`\n💰 **Asosiy balansingiz:** {u[0]:,} so\'m\n👥'
      f" **Taklif qilgan do'stlaringiz:** {u[1]} ta\n🌾 **Fermangizdagi"
      f' hayvonlar:** {animals_text}'
  )
  bot.send_message(message.chat.id, text, parse_mode='Markdown')


@bot.message_handler(func=lambda msg: msg.text == '🔗 Referal')
def show_ref(message):
  first_name = message.from_user.first_name
  ref_link = f'https://t.me/{BOT_USERNAME}?start=r{message.from_user.id}'

  caption = (
      f"✅ **Do'stingizni taklif qilish orqali ham ma'lum bir miqdorda"
      f' daromat oling!**💰\n\n📍 [{first_name}](tg://user?id={message.from_user.id})'
      " do'stingizdan havola-taklifnoma.\n\nDo'stingizni botimizga taklif"
      " qiling agar do'stingiz bo'limidan hayvon sotib olsa sizning"
      ' hisobingizga 10% miqdorda bonus taqdim etiladi 💸\n\n⚡️ **Boshlash uchun'
      f' bosing:**\n{ref_link}'
  )

  markup = types.InlineKeyboardMarkup()
  markup.row(
      types.InlineKeyboardButton(
          '↗️ Ulashish',
          switch_inline_query=(
              f"Do'stingizni botimizga taklif qiling: {ref_link}"
          ),
      )
  )

  try:
    with open('logo.jpg', 'rb') as photo:
      bot.send_photo(
          message.chat.id,
          photo,
          caption=caption,
          parse_mode='Markdown',
          reply_markup=markup,
      )
  except:
    bot.send_message(
        message.chat.id,
        caption,
        parse_mode='Markdown',
        reply_markup=markup,
        disable_web_page_preview=True,
    )


@bot.message_handler(func=lambda msg: msg.text == '💸 Pul kiritish')
def deposit_start(message):
  text = (
      f"💸 **Hisobingizni to'ldirmoqchi bo'lsangiz, quyidagi kartaga to'lov"
      f' qiling.**\n\n💳 **Karta:** `{CARD_NUMBER}`\n\n👤 **Quyidagi kartaga'
      " to'lov qiling va to'lov chekini yuboring.**\n\n▫️ 24000 so'm dan kamroq"
      ' kiritilgan pullar tushurib berilmaydi.'
  )
  markup = types.InlineKeyboardMarkup()
  markup.row(
      types.InlineKeyboardButton(
          "✅ To'lovni amalga oshirdim", callback_data='pay_done'
      )
  )
  bot.send_message(
      message.chat.id, text, parse_mode='Markdown', reply_markup=markup
  )


@bot.callback_query_handler(func=lambda call: call.data == 'pay_done')
def pay_done_callback(call):
  user_states[call.from_user.id] = 'waiting_for_check'
  text = (
      f"👨‍💼 **To'lov kvitansiyasi (chekini) yuboring.**\n\n**Eslatma:**\n▪️"
      ' Chekda sana, vaqt, ism familiya miqdor to\'liq ko\'rinishi kerak!\n▪️'
      ' Soxta chek yasash yoki umuman to\'lov qilmaslik, bloklanishga sabab'
      ' bo\'ladi.'
  )
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
  markup.row('⬅️ Ortga qaytish')
  bot.send_message(
      call.message.chat.id, text, parse_mode='Markdown', reply_markup=markup
  )


@bot.message_handler(func=lambda msg: msg.text == '⬅️ Ortga qaytish')
def back_to_main_menu(message):
  user_states.pop(message.from_user.id, None)
  bot.send_message(
      message.chat.id,
      '▪️ **Bosh sahifaga hush kelibsiz.**',
      reply_markup=get_main_menu(),
      parse_mode='Markdown',
  )


@bot.message_handler(
    content_types=['photo', 'document'],
    func=lambda msg: user_states.get(msg.from_user.id) == 'waiting_for_check',
)
def handle_check_upload(message):
  user_states.pop(message.from_user.id, None)
  bot.send_message(
      message.chat.id,
      "✅ **Chekingiz qabul qilindi. Operatorlar ko'rib chiqqach balansingiz"
      ' to\'ldiriladi!**',
      reply_markup=get_main_menu(),
      parse_mode='Markdown',
  )

  bot.send_message(
      ADMIN_ID,
      f"📥 **Yangi to'lov cheki keldi!**\nFoydalanuvchi:"
      f' @{message.from_user.username} (ID: `{message.from_user.id}`)',
      parse_mode='Markdown',
  )
  if message.photo:
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id)
  elif message.document:
    bot.send_document(ADMIN_ID, message.document.file_id)


@bot.message_handler(func=lambda msg: msg.text == '💰 Pul yechish')
def withdraw_info(message):
  u = get_user(message.from_user.id)
  text = f'💰 **Sizning balansingizda {u[0]} so\'m bor.**'
  markup = types.InlineKeyboardMarkup()
  markup.row(
      types.InlineKeyboardButton(
          '💰 Yechib olish', callback_data='withdraw_action'
      )
  )
  bot.send_message(
      message.chat.id, text, parse_mode='Markdown', reply_markup=markup
  )


@bot.callback_query_handler(func=lambda call: call.data == 'withdraw_action')
def withdraw_action(call):
  bot.answer_callback_query(
      call.id, '⚠️ Minimal pul yechish miqdori: 20,000 so\'m!', show_alert=True
  )


@bot.message_handler(func=lambda msg: msg.text == '🐮 Hayvon sotib olish')
def show_shop(message):
  bot.send_message(
      message.chat.id,
      '🛒 **Xarid qilish uchun hayvonni tanlang:**',
      reply_markup=get_shop_inline(),
      parse_mode='Markdown',
  )


@bot.callback_query_handler(func=lambda call: call.data.startswith('view_'))
def view_animal(call):
  key = call.data.split('_')[1]
  item = ANIMALS[key]

  text = (
      f"Hayvon nomi: {item['name']}\n\n▫️ Hayvon narxi {item['price']:,}"
      f" so'm\n▫️ Kunlik daromad: {item['daily']:,} so'm\n▫️ Umumiy daromad:"
      f" {item['total']:,} so'm\n\n✅ **Hayvon 30 kun davomida sizga foyda"
      " keltiradi. 30 kundan so'ng daromad berish vaqti"
      ' tugaydi.**\n\n🛒 Ushbu Hayvonni sotib olmoqchi bo\'lsangiz sotib olish'
      ' tugmasini bosing ⚡'
  )

  markup = types.InlineKeyboardMarkup()
  markup.row(
      types.InlineKeyboardButton(
          '💸 Sotib olish', callback_data=f'buy_{key}'
      )
  )
  markup.row(
      types.InlineKeyboardButton('⬅️ Orqaga', callback_data='back_to_shop')
  )

  bot.edit_message_text(
      text,
      call.message.chat.id,
      call.message.message_id,
      reply_markup=markup,
      parse_mode='Markdown',
  )


@bot.callback_query_handler(func=lambda call: call.data == 'back_to_shop')
def back_shop(call):
  bot.edit_message_text(
      '🛒 **Xarid qilish uchun hayvonni tanlang:**',
      call.message.chat.id,
      call.message.message_id,
      reply_markup=get_shop_inline(),
      parse_mode='Markdown',
  )


@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def buy_animal(call):
  key = call.data.split('_')[1]
  user_id = call.from_user.id
  u = get_user(user_id)
  item = ANIMALS[key]

  if u[0] < item['price']:
    bot.answer_callback_query(
        call.id, '❌ Balans yetarli emas!', show_alert=True
    )
    return

  now = int(time.time())
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()

  cursor.execute(
      'UPDATE users SET balance = balance - ? WHERE user_id = ?',
      (item['price'], user_id),
  )
  cursor.execute(
      'INSERT INTO user_animals (user_id, animal_key, buy_time, last_harvest)'
      ' VALUES (?, ?, ?, ?)',
      (user_id, key, now, now),
  )

  cursor.execute('SELECT referrer_id FROM users WHERE user_id = ?', (user_id,))
  ref_row = cursor.fetchone()
  if ref_row and ref_row[0]:
    ref_id = ref_row[0]
    bonus = int(item['price'] * 0.10)
    cursor.execute(
        'UPDATE users SET balance = balance + ? WHERE user_id = ?',
        (bonus, ref_id),
    )
    try:
      bot.send_message(
          ref_id,
          "🎉 **Taklif qilgan do'stingiz hayvon sotib oldi!**\nSizga"
          f" **{bonus:,} so'm** (10%) bonus berildi!",
          parse_mode='Markdown',
      )
    except:
      pass

  conn.commit()
  conn.close()

  bot.answer_callback_query(
      call.id, f"✅ {item['name']} sotib olindi!", show_alert=True
  )
  bot.send_message(
      call.message.chat.id,
      f"🎉 **Tabriklaymiz! Siz {item['name']} sotib oldingiz!**",
      parse_mode='Markdown',
  )


if __name__ == '__main__':
  init_db()
  print('Mening Fermam Bot muvaffaqiyatli ishga tushdi!')

  # Veb-serverni alohida oqimda (thread) ishga tushiramiz
  t = threading.Thread(target=run_web)
  t.daemon = True
  t.start()

  # Botni ishga tushiramiz
  bot.infinity_polling()
