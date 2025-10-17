import os
import asyncio
from datetime import datetime
from typing import Optional, List, Tuple

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import aiosqlite

# === BOT TOKENNI TO‘G‘RIDAN-TO‘G‘RI SHU YERDA YOZASIZ ===
BOT_TOKEN = "8000578476:AAG6OzBzxslSD6JwLvE4HbHmLygMh8BSBjA"  # <-- bu joyga tokeningizni yozing
ADMIN_ID = 5589736243
# o‘zingizning Telegram ID’ingiz (ixtiyoriy)

# === Agar token kiritilmagan bo‘lsa, xato chiqaradi ===
if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    raise RuntimeError("Iltimos, kod ichidagi BOT_TOKEN o‘rniga haqiqiy tokeningizni yozing.")

# ✅ Yangi versiyaga mos — parse_mode bu yerda belgilanadi
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
DBFILE = "schedule.db"
scheduler = AsyncIOScheduler()

# --- DB yordamchi funksiyalar ---
async def init_db():
    async with aiosqlite.connect(DBFILE) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            first_name TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL,
            time TEXT NOT NULL,
            text TEXT NOT NULL
        )
        """)
        await db.commit()

async def add_user(chat_id: int, first_name: Optional[str]):
    async with aiosqlite.connect(DBFILE) as db:
        await db.execute("INSERT OR REPLACE INTO users (chat_id, first_name) VALUES (?, ?)", (chat_id, first_name or ""))
        await db.commit()

async def get_all_users() -> List[int]:
    async with aiosqlite.connect(DBFILE) as db:
        cur = await db.execute("SELECT chat_id FROM users")
        rows = await cur.fetchall()
        return [r[0] for r in rows]

async def get_schedules_for_day(day: str) -> List[Tuple[int, str, str]]:
    async with aiosqlite.connect(DBFILE) as db:
        cur = await db.execute("SELECT id, time, text FROM schedules WHERE day=? ORDER BY time", (day,))
        rows = await cur.fetchall()
        return [(r[0], r[1], r[2]) for r in rows]

async def list_schedules() -> List[Tuple[int, str, str, str]]:
    async with aiosqlite.connect(DBFILE) as db:
        cur = await db.execute("SELECT id, day, time, text FROM schedules ORDER BY id")
        rows = await cur.fetchall()
        return [(r[0], r[1], r[2], r[3]) for r in rows]

# --- Foydali funksiyalar ---
def get_weekdays_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    days = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma"]
    for day in days:
        builder.add(KeyboardButton(text=day))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# --- Komandalar ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await add_user(message.chat.id, message.from_user.first_name if message.from_user else "")
    txt = (
        "Assalomu alaykum! 👋\n\n"
        "Men kunlik dars jadvalini yuboruvchi botman.\n\n"
        "Buyruqlar:\n"
        "/today - bugungi jadval\n"
        "/week - haftalik jadval\n"
        "/help - yordam"
    )
    await message.answer(txt, reply_markup=get_weekdays_keyboard())

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("Buyruqlar: /today, /week yoki hafta kunini tanlang.")

# --- Haftalik tugmalar ---
@dp.message(F.text.in_(["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma"]))
async def handle_day_button(message: Message):
    day_map = {
        "Dushanba": "dushanba",
        "Seshanba": "seshanba",
        "Chorshanba": "chorshanba",
        "Payshanba": "payshanba",
        "Juma": "juma",
    }
    day_name = day_map[message.text]
    rows = await get_schedules_for_day(day_name)

    if not rows:
        await message.answer(f"{message.text} kuniga jadval yo‘q.")
        return

    lines = [f"<b>{message.text} — dars jadvali</b>"]
    for _, t, txt in rows:
        lines.append(f"{t} — {txt}")
    await message.answer("\n".join(lines))

@dp.message(Command("today"))
async def cmd_today(message: Message):
    weekday = datetime.utcnow().astimezone().weekday()
    order = ["dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba"]
    today = order[weekday]
    rows = await get_schedules_for_day(today)
    if not rows:
        await message.answer("Bugungi kun uchun jadval topilmadi.")
        return
    lines = [f"<b>{today.capitalize()} — dars jadvali</b>"]
    for _, t, txt in rows:
        lines.append(f"{t} — {txt}")
    await message.answer("\n".join(lines))

@dp.message(Command("week"))
async def cmd_week(message: Message):
    rows = await list_schedules()
    if not rows:
        await message.answer("Hali jadval qo‘shilmagan.")
        return
    grouped = {}
    for _, day, t, txt in rows:
        grouped.setdefault(day, []).append((t, txt))
    out = []
    for d, data in grouped.items():
        out.append(f"<b>{d.capitalize()}</b>")
        for t, txt in data:
            out.append(f"{t} — {txt}")
        out.append("")
    await message.answer("\n".join(out))

# --- Jadvalni avtomatik to‘ldirish ---
async def preload_schedule():
    lessons = {
        "dushanba": [
            ("08:30", "Chiziqli algebra — 6B- 202 / Ma’ruza / ZIYAYEV U.M."),
            ("10:00", "Diskret tuzilmalar — 6B-306 / Ma’ruza / SATTOROV M.E."),
            ("11:30", " Kiberxavsizlik asoslari - 6B- 303 / Ma'ruza /  UZAQOV O.SH."),
        ],
        "seshanba": [
            ("08:30", "Diskret tuzilmalar — 6B-202 / Ma’ruza / SATTOROV M.E."),
            ("10:00", "Elektronika va sxemalar 1 — 6B-208 / Laboratoriya / ABDURAXMONOVA M.A."),
            ("11:30",  " Kiberxavsizlik asoslari - 6B-205 / Amaliy /  UZAQOV O.SH." ),
        ],
        "chorshanba": [
            ("08:30", "Sun’iy intellekt asoslari — 6B-204 / Ma’ruza / ACHILOVA F.K."),
            ("10:00", "Elektronika va sxemalar 1 — 6B- 303 / Ma'ruza / NAZAROV B.S."),
             ("10:00", "Elektronika va sxemalar 1 — 6B- 202 / Ma'ruza / NAZAROV B.S."), 
        ],
        "payshanba": [
            ("08:30", "Kiberxavfsizlik asoslari — 6B-202 / Ma’ruza / UZAQOV O.SH."),
            ("10:00", "Murabbiylik soati  — 6B-202 / Ma'ruza / NAZAROV B.S."),
             ("11:30", "Sun’iy intellekt asoslari — 6B-303 / Ma’ruza / ACHILOVA F.K."),
        ],
        "juma": [
            ("10:00", "Sun’iy intellekt asoslari — 6B-111 / Amaliy / ACHILOVA F.K."),
             ("08:30", "Chiziqli algebra — 6B- 305 / Amaliy / ZIYAYEV U.M."),
        ]
    }

    async with aiosqlite.connect(DBFILE) as db:
        cur = await db.execute("SELECT COUNT(*) FROM schedules")
        count = (await cur.fetchone())[0]
        if count == 0:
            for day, data in lessons.items():
                for t, txt in data:
                    await db.execute("INSERT INTO schedules (day, time, text) VALUES (?, ?, ?)", (day, t, txt))
            await db.commit()

# --- Asosiy ishga tushirish ---
async def main():
    import logging
    logging.basicConfig(level=logging.INFO)
    await init_db()
    await preload_schedule()
    scheduler.start()
    print("✅ Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
