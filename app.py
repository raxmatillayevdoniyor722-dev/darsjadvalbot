import os
import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

# === TOKEN shu yerda ===
BOT_TOKEN = "8000578476:AAG6OzBzxslSD6JwLvE4HbHmLygMh8BSBjA"
DBFILE = "schedule.db"
GROUP_ID = "@kompyuter_Xizmatlariiiii"  # Guruh username yoki ID

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

# --- Dars jadvali tayyorlash ---
def preload_schedule():
    lessons = {
        "dushanba": [
            ("08:30", "Chiziqli algebra — 6B-202 / Ma'ruza / ZIYAYEV U.M."),
            ("10:00", "Diskret tuzilmalar — 6B-306 / Ma'ruza / SATTOROV M.E."),
            ("11:30", "Kiberxavfsizlik asoslari - 6B-303 / Ma'ruza / UZAQOV O.SH."),
        ],
        "seshanba": [
            ("08:30", "Diskret tuzilmalar — 6B-202 / Ma'ruza / SATTOROV M.E."),
            ("10:00", "Elektronika va sxemalar 1 — 6B-208 / Laboratoriya / ABDURAXMONOVA M.A."),
            ("11:30", "Kiberxavfsizlik asoslari - 6B-205 / Amaliy / UZAQOV O.SH."),
        ],
        "chorshanba": [
            ("08:30", "Sun'iy intellekt asoslari — 6B-204 / Ma'ruza / ACHILOVA F.K."),
            ("10:00", "Elektronika va sxemalar 1 — 6B-303 / Ma'ruza / NAZAROV B.S."),
        ],
        "payshanba": [
            ("08:30", "Kiberxavfsizlik asoslari — 6B-202 / Ma'ruza / UZAQOV O.SH."),
            ("10:00", "Murabbiylik soati  — 6B-202 / Ma'ruza / NAZAROV B.S."),
            ("11:30", "Sun'iy intellekt asoslari — 6B-303 / Ma'ruza / ACHILOVA F.K."),
        ],
        "juma": [
            ("08:30", "Chiziqli algebra — 6B-305 / Amaliy / ZIYAYEV U.M."),
            ("10:00", "Sun'iy intellekt asoslari — 6B-111 / Amaliy / ACHILOVA F.K."),
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

# --- Ma'lumotni olish ---
def get_day_schedule(day):
    conn = sqlite3.connect(DBFILE)
    cur = conn.cursor()
    cur.execute("SELECT time, text FROM schedules WHERE day=? ORDER BY time", (day,))
    rows = cur.fetchall()
    conn.close()
    return rows

# --- Guruh a'zoligini tekshirish ---
async def is_group_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(GROUP_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Guruh a'zoligini tekshirishda xato: {e}")
        return False

# --- Guruhga qo'shilish so'rovi ---
async def send_group_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["📢 Guruhga qo'shilish"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    text = (
        "❌ Botdan foydalanish uchun avval guruhimizga a'zo bo'lishingiz kerak!\n\n"
        "Quyidagi tugma orqali guruhga qo'shiling va keyin /start ni bosing:\n"
        "https://t.me/kompyuter_Xizmatlariiiii"
    )
    await update.message.reply_text(text, reply_markup=markup)

# --- Komandalar ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Guruh a'zoligini tekshirish
    if not await is_group_member(user_id, context):
        await send_group_request(update, context)
        return
    
    # Agar guruh a'zosi bo'lsa
    keyboard = [["Dushanba", "Seshanba"], ["Chorshanba", "Payshanba"], ["Juma"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    text = (
        "Assalomu alaykum 👋\n"
        "Guruhga a'zo bo'lganingiz uchun rahmat!\n"
        "Men kunlik dars jadvalini yuboruvchi botman.\n\n"
        "Buyruqlar:\n"
        "/today - bugungi jadval\n"
        "/week - haftalik jadval\n"
        "Yoki hafta kunini tanlang ⬇️"
    )
    await update.message.reply_text(text, reply_markup=markup)

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Guruh a'zoligini tekshirish
    if not await is_group_member(user_id, context):
        await send_group_request(update, context)
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

async def week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Guruh a'zoligini tekshirish
    if not await is_group_member(user_id, context):
        await send_group_request(update, context)
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

async def day_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Guruh a'zoligini tekshirish
    if not await is_group_member(user_id, context):
        await send_group_request(update, context)
        return
    
    text = update.message.text.lower()
    
    # Agar "guruhga qo'shilish" tugmasi bosilsa
    if "guruhga qo'shilish" in text.lower() or "📢" in text:
        await send_group_request(update, context)
        return
        
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

    # Conflict xatosini oldini olish uchun
    request = HTTPXRequest(connection_pool_size=8)
    
    app = Application.builder().token(BOT_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("week", week))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, day_button))

    print("✅ Bot ishga tushdi...")
    
    # Webhook o'rniga polling ishlatamiz, lekin timeout va pool_size bilan
    app.run_polling(
        poll_interval=1.0,
        timeout=20,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
