import os
import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# === TOKEN va GURUHINGIZ ID'si ===
BOT_TOKEN = "8000578476:AAG6OzBzxslSD6JwLvE4HbHmLygMh8BSBjA"
GROUP_ID = -7750409176  # Guruhingiz ID raqami
DBFILE = "schedule.db"

# --- Jadvalni yaratish yoki yangilash ---
def init_db():
    conn = sqlite3.connect(DBFILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL,
            time TEXT NOT NULL,
            text TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# --- Jadvalni dastlab to‘ldirish ---
def preload_schedule():
    lessons = {
        "dushanba": [
            ("08:30", "Chiziqli algebra — 6B-202 / Ma’ruza / ZIYAYEV U.M."),
            ("10:00", "Diskret tuzilmalar — 6B-306 / Ma’ruza / SATTOROV M.E."),
            ("11:30", "Kiberxavfsizlik asoslari - 6B-303 / Ma'ruza / UZAQOV O.SH."),
        ],
        "seshanba": [
            ("08:30", "Diskret tuzilmalar — 6B-202 / Ma’ruza / SATTOROV M.E."),
            ("10:00", "Elektronika va sxemalar 1 — 6B-208 / Laboratoriya / ABDURAXMONOVA M.A."),
            ("11:30", "Kiberxavfsizlik asoslari - 6B-205 / Amaliy / UZAQOV O.SH."),
        ],
        "chorshanba": [
            ("08:30", "Sun’iy intellekt asoslari — 6B-204 / Ma’ruza / ACHILOVA F.K."),
            ("10:00", "Elektronika va sxemalar 1 — 6B-303 / Ma'ruza / NAZAROV B.S."),
        ],
        "payshanba": [
            ("08:30", "Kiberxavfsizlik asoslari — 6B-202 / Ma’ruza / UZAQOV O.SH."),
            ("10:00", "Murabbiylik soati  — 6B-202 / Ma'ruza / NAZAROV B.S."),
            ("11:30", "Sun’iy intellekt asoslari — 6B-303 / Ma’ruza / ACHILOVA F.K."),
        ],
        "juma": [
            ("08:30", "Chiziqli algebra — 6B-305 / Amaliy / ZIYAYEV U.M."),
            ("10:00", "Sun’iy intellekt asoslari — 6B-111 / Amaliy / ACHILOVA F.K."),
        ]
    }

    conn = sqlite3.connect(DBFILE)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM schedules")
    if cur.fetchone()[0] == 0:
        for day, data in lessons.items():
            for t, txt in data:
                cur.execute("INSERT INTO schedules (day, time, text) VALUES (?, ?, ?)", (day, t, txt))
        conn.commit()
    conn.close()

# --- Ma'lumot olish ---
def get_day_schedule(day):
    conn = sqlite3.connect(DBFILE)
    cur = conn.cursor()
    cur.execute("SELECT time, text FROM schedules WHERE day=? ORDER BY time", (day,))
    rows = cur.fetchall()
    conn.close()
    return rows

# --- Guruh a’zoligini tekshirish funksiyasi ---
async def is_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(GROUP_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
        else:
            return False
    except Exception:
        return False

# --- /start komandasi ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update, context):
        await update.message.reply_text(
            "❌ Botdan foydalanish uchun avval guruhga a’zo bo‘ling:\n"
            "👉 https://t.me/kompyuter_Xizmatlariiiii"
        )
        return

    keyboard = [["Dushanba", "Seshanba"], ["Chorshanba", "Payshanba"], ["Juma"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    text = (
        "Assalomu alaykum 👋\n"
        "Men kunlik dars jadvalini yuboruvchi botman.\n\n"
        "Buyruqlar:\n"
        "/today - bugungi jadval\n"
        "/week - haftalik jadval\n"
        "Yoki hafta kunini tanlang ⬇️"
    )
    await update.message.reply_text(text, reply_markup=markup)

# --- /today komandasi ---
async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update, context):
        await update.message.reply_text(
            "❌ Botdan foydalanish uchun guruhga a’zo bo‘ling:\n👉 https://t.me/kompyuter_Xizmatlariiiii"
        )
        return

    days = ["dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba"]
    today = days[datetime.now().weekday()]
    rows = get_day_schedule(today)
    if not rows:
        await update.message.reply_text("Bugungi kun uchun jadval topilmadi.")
        return
    txt = f"<b>{today.capitalize()} — dars jadvali</b>\n"
    for t, subject in rows:
        txt += f"{t} — {subject}\n"
    await update.message.reply_html(txt)

# --- /week komandasi ---
async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update, context):
        await update.message.reply_text(
            "❌ Botdan foydalanish uchun guruhga a’zo bo‘ling:\n👉 https://t.me/kompyuter_Xizmatlariiiii"
        )
        return

    conn = sqlite3.connect(DBFILE)
    cur = conn.cursor()
    cur.execute("SELECT day, time, text FROM schedules ORDER BY id")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Hali jadval mavjud emas.")
        return

    grouped = {}
    for day, time, text in rows:
        grouped.setdefault(day, []).append((time, text))

    msg = ""
    for d, data in grouped.items():
        msg += f"<b>{d.capitalize()}</b>\n"
        for t, txt in data:
            msg += f"{t} — {txt}\n"
        msg += "\n"
    await update.message.reply_html(msg)

# --- Matn orqali kun tanlash ---
async def day_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_member(update, context):
        await update.message.reply_text(
            "❌ Botdan foydalanish uchun guruhga a’zo bo‘ling:\n👉 https://t.me/kompyuter_Xizmatlariiiii"
        )
        return

    text = update.message.text.lower()
    rows = get_day_schedule(text)
    if not rows:
        await update.message.reply_text(f"{update.message.text} kuniga jadval topilmadi.")
        return
    msg = f"<b>{text.capitalize()} — dars jadvali</b>\n"
    for t, subject in rows:
        msg += f"{t} — {subject}\n"
    await update.message.reply_html(msg)

# --- Asosiy ishga tushirish ---
def main():
    init_db()
    preload_schedule()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("week", week))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, day_button))

    print("✅ Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
