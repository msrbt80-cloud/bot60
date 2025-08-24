# -*- coding: utf-8 -*-
"""
بوت تيليجرام لعبة أرقام مع اشتراك إجباري في قناة @UU24Z
- يرد فقط عندما يرسل المستخدم أوامر اللعبة.
- عند كتابة الحرف "ر" → رقم عشوائي من 1 إلى 999,999 مع فواصل.
- إذا كتب الرقم صح → نقطة، يظهر وقت الاستجابة بالثواني.
- عند كتابة "نقاطي" → يظهر له نقاطه الحالية.
- عند كتابة "/reset" → يعيد النقاط واللعبة.
- عند كتابة "ترتيب" → يظهر أفضل 6 لاعبين حسب النقاط.
- عند كتابة "الأوامر" أو "قائمة الأوامر" → يظهر جميع أوامر البوت.
- لا يستخدم البوت أي ايموجيات، فقط نص وعلامة صح.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters
)
import logging
import sqlite3
import random
from datetime import datetime

# ------------------ CONFIGURATION ------------------
TOKEN = "7556325165:AAFyUp-au0QUyVqTZqCkWXNvMTiw0U1cAE4"
DB_PATH = "bot_game.db"
WELCOME_MESSAGE = "أهلاً بك! أرسل الحرف (ر) لتبدأ اللعبة."
CHANNEL_USERNAME = "@UU24Z"
# ---------------------------------------------------

# ------ Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------ Database helpers
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        points INTEGER DEFAULT 0,
                        current_number INTEGER,
                        start_time TEXT,
                        updated_at TEXT
                    )''')
        conn.commit()

def add_user(user):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''INSERT OR IGNORE INTO users 
                     (user_id, username, first_name, points, current_number, start_time, updated_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (user.id, user.username, user.first_name or "", 0, None, None, datetime.utcnow().isoformat()))
        conn.commit()

def set_current_number(user_id, number):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('UPDATE users SET current_number=?, start_time=?, updated_at=? WHERE user_id=?',
                  (number, datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), user_id))
        conn.commit()

def get_user(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('SELECT points, current_number, start_time FROM users WHERE user_id=?', (user_id,))
        row = c.fetchone()
    return row

def add_point(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('UPDATE users SET points = points + 1, current_number=NULL, start_time=NULL, updated_at=? WHERE user_id=?',
                  (datetime.utcnow().isoformat(), user_id))
        conn.commit()

def reset_user(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('UPDATE users SET points=0, current_number=NULL, start_time=NULL, updated_at=? WHERE user_id=?',
                  (datetime.utcnow().isoformat(), user_id))
        conn.commit()

# ------ Subscription check
async def check_subscription(user_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ['member', 'creator', 'administrator']:
            return True
        return False
    except Exception as e:
        logger.error(f"خطأ في التحقق من الاشتراك: {e}")
        return False

# ------ Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user)
    await update.message.reply_text(WELCOME_MESSAGE)

async def play_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user)
    text = update.message.text.strip()

    if text not in ["ر", "نقاطي", "ترتيب", "الأوامر", "قائمة الأوامر"] and not text.replace(',', '').isdigit():
        return

    subscribed = await check_subscription(user.id, context)
    if not subscribed:
        keyboard = [[InlineKeyboardButton("اشترك في القناة أولاً", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]]
        await update.message.reply_text("يجب أن تكون مشتركاً في القناة لتلعب اللعبة", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if text == "ر":
        number = random.randint(1, 999999)
        set_current_number(user.id, number)
        formatted_number = f"{number:,}"
        await update.message.reply_text(f"اكتب الرقم التالي بسرعة: {formatted_number}")
        return

    if text.replace(',', '').isdigit():
        row = get_user(user.id)
        if not row:
            add_user(user)
            return
        points, current_number, start_time_str = row
        if current_number and int(text.replace(',', '')) == current_number:
            if start_time_str:
                start_time = datetime.fromisoformat(start_time_str)
                delta_seconds = (datetime.utcnow() - start_time).total_seconds()
            else:
                delta_seconds = 0
            add_point(user.id)
            new_points, _, _ = get_user(user.id)
            await update.message.reply_text(f"احسنت! استغرقت {delta_seconds:.2f} ثانية. مجموع نقاطك: {new_points}. ارسل (ر) لنكمل")
        else:
            await update.message.reply_text("الرقم غير صحيح. جرب من جديد وأرسل (ر)")
        return

    if text == "نقاطي":
        row = get_user(user.id)
        if row:
            points, _, _ = row
            await update.message.reply_text(f"لديك {points} نقطة")
        else:
            await update.message.reply_text("ليس لديك أي نقاط بعد. أرسل (ر) لتبدأ")
        return

    if text == "ترتيب":
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('SELECT username, first_name, points FROM users ORDER BY points DESC LIMIT 6')
            rows = c.fetchall()

        if not rows:
            await update.message.reply_text("لا يوجد لاعبين بعد.")
            return

        leaderboard_text = "ترتيب أفضل 6 لاعبين:\n\n"
        for i, row in enumerate(rows, start=1):
            username, first_name, points = row
            name_display = username or first_name or "مستخدم مجهول"
            leaderboard_text += f"{i}. {name_display} - {points} نقطة\n"

        await update.message.reply_text(leaderboard_text)
        return

    if text in ["الأوامر", "قائمة الأوامر"]:
        await show_commands(update, context)
        return

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    reset_user(user.id)
    await update.message.reply_text("تم إعادة تعيين نقاطك واللعبة بنجاح. أرسل (ر) لتبدأ من جديد.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أرسل (ر) ليعطيك البوت رقم عشوائي مع فواصل، إذا كتبته بشكل صحيح تحصل على نقطة مع حساب الوقت بالثواني. الاشتراك في القناة مطلوب.\n"
        "أرسل 'نقاطي' لمعرفة نقاطك.\n"
        "أرسل /reset لإعادة اللعبة.\n"
        "أرسل 'ترتيب' لمعرفة أفضل 6 لاعبين.\n"
        "أرسل 'الأوامر' أو 'قائمة الأوامر' لعرض جميع أوامر البوت."
    )

async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    commands_text = (
        "قائمة أوامر البوت:\n\n"
        "ر → للحصول على رقم عشوائي لتبدأ اللعبة\n"
        "نقاطي → لمعرفة عدد نقاطك الحالية\n"
        "ترتيب → عرض أفضل 6 لاعبين حسب النقاط\n"
        "/reset → إعادة تعيين نقاطك واللعبة\n"
        "الأوامر أو قائمة الأوامر → عرض جميع أوامر البوت\n"
        "/help → شرح كيفية اللعب"
    )
    await update.message.reply_text(commands_text)

# ------ Main
if __name__ == '__main__':
    init_db()
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_cmd))
    application.add_handler(CommandHandler('reset', reset_cmd))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, play_game))

    print('Bot is running...')
    application.run_polling()
