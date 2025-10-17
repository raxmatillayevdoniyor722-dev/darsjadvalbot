# bot_with_buttons.py
import os
import asyncio
from datetime import datetime, time
from typing import Optional, List, Tuple

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import aiosqlite
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("8000578476:AAG6OzBzxslSD6JwLvE4HbHmLygMh8BSBjA")
ADMIN_ID = int(os.getenv("5589736243", "0"))

if not BOT_TOKEN:
    raise RuntimeError("Iltimos .env faylga BOT_TOKEN qo'ying")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
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
            day TEXT NOT NULL,         -- dushanba, seshanba, chorshanba, payshanba, juma, shanba, yakshanba
            time TEXT NOT NULL,        -- hh:mm (matn)
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


async def set_schedule(day: str, t: str, text: str):
    async with aiosqlite.connect(DBFILE) as db:
        await db.execute("INSERT INTO schedules (day, time, text) VALUES (?, ?, ?)", (day, t, text))
        await db.commit()


async def update_schedule(sid: int, day: str, t: str, text: str):
    async with aiosqlite.connect(DBFILE) as db:
        await db.execute("UPDATE schedules SET day=?, time=?, text=? WHERE id=?", (day, t, text, sid))
        await db.commit()


async def delete_schedule(sid: int):
    async with aiosqlite.connect(DBFILE) as db:
        await db.execute("DELETE FROM schedules WHERE id=?", (sid,))
        await db.commit()


async def list_schedules() -> List[Tuple[int, str, str, str]]:
    async with aiosqlite.connect(DBFILE) as db:
        cur = await db.execute("SELECT id, day, time, text FROM schedules ORDER BY id")
        rows = await cur.fetchall()
        return [(r[0], r[1], r[2], r[3]) for r in rows]


async def get_schedules_for_day(day: str) -> List[Tuple[int, str, str]]:
    async with aiosqlite.connect(DBFILE) as db:
        cur = await db.execute("SELECT id, time, text FROM schedules WHERE day=? ORDER BY time", (day,))
        rows = await cur.fetchall()
        return [(r[0], r[1], r[2]) for r in rows]


# --- util ---
UZ_DAYS = {
    "dushanba": "dushanba",
    "seshanba": "seshanba",
    "chorshanba": "chorshanba",
    "payshanba": "payshanba",
    "juma": "juma",
    "shanba": "shanba",
    "yakshanba": "yakshanba"
}

def normalize_day(s: str) -> Optional[str]:
    s2 = s.strip().lower()
    return UZ_DAYS.get(s2)


def is_admin(user_id: int) -> bool:
    return ADMIN_ID and user_id == ADMIN_ID


# --- Keyboard yaratish ---
def get_weekdays_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    days = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
    for day in days:
        builder.add(KeyboardButton(text=day))
    builder.adjust(2)  # 2 ta ustun
    return builder.as_markup(resize_keyboard=True)


# --- bot handlers ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await add_user(message.chat.id, message.from_user.first_name if message.from_user else "")
    txt = (
        "Assalomu alaykum! 👋\n\n"
        "Men kunlik dars jadvalini yuboruvchi botman.\n\n"
        "Quyidagi tugmalar orqali istalgan kunning jadvalini ko'rishingiz mumkin:\n\n"
        "Buyruqlar:\n"
        "/today - bugungi jadvalni ko'rsatadi\n"
        "/week - haftalik jadval\n"
        "/help - yordam\n\n"
        "Administrator uchun:\n"
        "/set <kun> <hh:mm> | <matn>  - yangi jadval qo'shish\n"
        "/list - barcha jadvalni ko'rsatish\n"
        "/del <id> - jadvalni o'chirish\n"
        "/keyboard - hafta kunlari tugmalarini ko'rsatish\n"
        "/hide - tugmalarni yashirish"
    )
    await message.answer(txt, reply_markup=get_weekdays_keyboard())


@dp.message(Command("keyboard"))
async def cmd_keyboard(message: Message):
    await message.answer("Hafta kunlari tugmalari:", reply_markup=get_weekdays_keyboard())


@dp.message(Command("hide"))
async def cmd_hide(message: Message):
    await message.answer("Tugmalar yashirildi.", reply_markup=ReplyKeyboardRemove())


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("Yuqoridagi buyruqlar orqali ishlatishingiz mumkin. /start bilan qaytadan boshlash mumkin.")


# Hafta kunlari tugmalariga javob
@dp.message(F.text.in_(["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]))
async def handle_day_button(message: Message):
    day_map = {
        "Dushanba": "dushanba",
        "Seshanba": "seshanba", 
        "Chorshanba": "chorshanba",
        "Payshanba": "payshanba",
        "Juma": "juma",
        "Shanba": "shanba",
        "Yakshanba": "yakshanba"
    }
    
    day_name = day_map[message.text]
    rows = await get_schedules_for_day(day_name)
    
    if not rows:
        await message.answer(f"{message.text} kuniga jadval qo'shilmagan.")
        return
        
    lines = [f"<b>{message.text} — jadval</b>"]
    for sid, t, txt in rows:
        lines.append(f"{t} — {txt}")
    
    await message.answer("\n".join(lines))


@dp.message(Command("today"))
async def cmd_today(message: Message):
    weekday = datetime.utcnow().astimezone().weekday()
    day_order = ["dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba"]
    today_name = day_order[weekday]
    
    # Uzbek kun nomi
    day_names_uz = {
        "dushanba": "Dushanba",
        "seshanba": "Seshanba", 
        "chorshanba": "Chorshanba",
        "payshanba": "Payshanba",
        "juma": "Juma",
        "shanba": "Shanba",
        "yakshanba": "Yakshanba"
    }
    
    rows = await get_schedules_for_day(today_name)
    if not rows:
        await message.answer(f"Bugun ({day_names_uz[today_name]}) uchun jadval topilmadi.")
        return
        
    lines = [f"<b>{day_names_uz[today_name]} — jadval</b>"]
    for sid, t, txt in rows:
        lines.append(f"{t} — {txt}")
        
    await message.answer("\n".join(lines))


@dp.message(Command("week"))
async def cmd_week(message: Message):
    rows = await list_schedules()
    if not rows:
        await message.answer("Hali jadval qo'shilmagan.")
        return
        
    grouped = {}
    for sid, day, t, txt in rows:
        grouped.setdefault(day, []).append((sid, t, txt))
        
    out = []
    day_names_uz = {
        "dushanba": "Dushanba",
        "seshanba": "Seshanba", 
        "chorshanba": "Chorshanba",
        "payshanba": "Payshanba",
        "juma": "Juma",
        "shanba": "Shanba",
        "yakshanba": "Yakshanba"
    }
    
    order = ["dushanba","seshanba","chorshanba","payshanba","juma","shanba","yakshanba"]
    for d in order:
        if d in grouped:
            out.append(f"<b>{day_names_uz[d]}</b>")
            for sid, t, txt in grouped[d]:
                out.append(f"{t} — {txt}")
            out.append("")  # bo'sh qator
            
    await message.answer("\n".join(out))


@dp.message(Command("list"))
async def cmd_list(message: Message):
    if not is_admin(message.from_user.id):
        await message.reply("Faqat admin foydalanishi mumkin.")
        return
        
    rows = await list_schedules()
    if not rows:
        await message.answer("Jadval ro'yxati bo'sh.")
        return
        
    lines = ["<b>Jadval ro'yxati:</b>"]
    for sid, day, t, txt in rows:
        lines.append(f"id:{sid} | {day} {t} — {txt}")
        
    await message.answer("\n".join(lines))


@dp.message(Command("del"))
async def cmd_del(message: Message):
    if not is_admin(message.from_user.id):
        await message.reply("Faqat admin foydalanishi mumkin.")
        return
        
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Foydalanish: /del <id>")
        return
        
    try:
        sid = int(args[1])
    except ValueError:
        await message.reply("Id raqam boʻlishi kerak.")
        return
        
    await delete_schedule(sid)
    await message.reply(f"Jadval id={sid} oʻchirildi (agar mavjud boʻlsa).")


@dp.message()
async def fallback(message: Message):
    text = message.text or ""
    if text.startswith("/set"):
        if not is_admin(message.from_user.id):
            await message.reply("Faqat admin foydalanishi mumkin.")
            return
            
        try:
            payload = text[len("/set"):].strip()
            if "|" not in payload:
                await message.reply("Format: /set <kun> <hh:mm> | <matn>\nMasalan: /set dushanba 09:00 | Matematika")
                return
                
            left, schedule_text = payload.split("|", 1)
            left = left.strip()
            schedule_text = schedule_text.strip()
            parts = left.split()
            
            if len(parts) < 2:
                await message.reply("Kun va vaqt kerak. Masalan: /set dushanba 09:00 | Matematika")
                return
                
            day_raw = parts[0]
            t_raw = parts[1]
            day = normalize_day(day_raw)
            
            if not day:
                await message.reply("Kun notoʻgʻri. Misol uchun: dushanba, seshanba, chorshanba, payshanba, juma, shanba, yakshanba")
                return
                
            try:
                hh, mm = t_raw.split(":")
                hh_i = int(hh); mm_i = int(mm)
                if not (0 <= hh_i < 24 and 0 <= mm_i < 60):
                    raise ValueError
            except Exception:
                await message.reply("Vaqt format xato. hh:mm tarzida kiriting, masalan 06:00")
                return
                
            await set_schedule(day, t_raw, schedule_text)
            await message.reply(f"Jadval qoʻshildi: {day} {t_raw} — {schedule_text}")
            await reschedule_daily_jobs()
            
        except Exception as e:
            await message.reply(f"Xatolik: {e}")
    else:
        await message.reply("Buyruqlar: /today /week. Adminlar uchun: /set, /list, /del\nYoki hafta kunlarini tanlang tugmalardan.")


# --- Scheduler ---
async def send_daily_schedule_to_all(day_name: str):
    rows = await get_schedules_for_day(day_name)
    if not rows:
        return
        
    day_names_uz = {
        "dushanba": "Dushanba",
        "seshanba": "Seshanba", 
        "chorshanba": "Chorshanba",
        "payshanba": "Payshanba",
        "juma": "Juma",
        "shanba": "Shanba",
        "yakshanba": "Yakshanba"
    }
    
    lines = [f"<b>{day_names_uz[day_name]} — dars jadvali</b>"]
    for sid, t, txt in rows:
        lines.append(f"{t} — {txt}")
        
    text = "\n".join(lines)
    users = await get_all_users()
    
    for chat_id in users:
        try:
            await bot.send_message(chat_id, text)
            await asyncio.sleep(0.05)
        except Exception:
            pass


async def reschedule_daily_jobs():
    scheduler.remove_all_jobs()
    rows = await list_schedules()
    
    triggers = {}
    for sid, day, t, txt in rows:
        key = (day, t)
        if key not in triggers:
            triggers[key] = True
            
    for (day, t) in triggers.keys():
        hh, mm = t.split(":")
        day_map = {
            "dushanba": "mon",
            "seshanba": "tue",
            "chorshanba": "wed",
            "payshanba": "thu", 
            "juma": "fri",
            "shanba": "sat",
            "yakshanba": "sun"
        }
        dow = day_map.get(day, None)
        if not dow:
            continue
            
        job_id = f"job_{day}_{t.replace(':','')}"
        trigger = CronTrigger(day_of_week=dow, hour=int(hh), minute=int(mm))
        
        scheduler.add_job(lambda d=day: asyncio.create_task(send_daily_schedule_to_all(d)),
                          trigger=trigger,
                          id=job_id,
                          replace_existing=True)


# --- start/stop hooks ---
async def on_startup():
    await init_db()
    await reschedule_daily_jobs()
    scheduler.start()


async def on_shutdown():
    await bot.session.close()
    scheduler.shutdown()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(on_startup())
        dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        asyncio.run(on_shutdown())
