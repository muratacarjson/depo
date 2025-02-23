
import asyncio
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import ChatPermissions
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.filters import Command
from aiogram.enums import ChatMemberStatus

# Telegram Bot API Token
API_TOKEN = "7818517016:AAGiG3hsYcvB2YG7L5Q0zPOsCsyokE87KYc"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# SQLite Database Connection
conn = sqlite3.connect("users.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    join_date TEXT
)
""")
conn.commit()

@dp.chat_member()
async def on_user_join(event: types.ChatMemberUpdated):
    if event.new_chat_member.status == ChatMemberStatus.MEMBER:
        user_id = event.new_chat_member.user.id
        group_id = event.chat.id
        join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT OR REPLACE INTO users (user_id, join_date) VALUES (?, ?)", (user_id, join_date))
        conn.commit()
        await bot.send_message(group_id, f"👋 {event.new_chat_member.user.full_name} gruba katıldı. Süresi 30 gün sonra dolacak.")

async def check_users():
    cursor.execute("SELECT user_id, join_date FROM users")
    users = cursor.fetchall()
    for user_id, join_date in users:
        join_date = datetime.strptime(join_date, "%Y-%m-%d %H:%M:%S")
        days_left = 30 - (datetime.now() - join_date).days
        if days_left <= 0:
            try:
                await bot.ban_chat_member(group_id, user_id)
                await bot.send_message(group_id, f"🚨 <a href='tg://user?id={user_id}'>Kullanıcı</a> süresi dolduğu için gruptan çıkarıldı.", parse_mode="HTML")
                cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
                conn.commit()
            except Exception as e:
                logging.error(f"Kullanıcıyı atarken hata oluştu: {e}")

@dp.message(Command("kalan_sure"))
async def show_remaining_time(message: types.Message):
    admin_id = message.from_user.id
    group_id = message.chat.id
    cursor.execute("SELECT user_id, join_date FROM users")
    users = cursor.fetchall()
    response = "📌 Kullanıcıların kalan süreleri:\n"
    for user_id, join_date in users:
        join_date = datetime.strptime(join_date, "%Y-%m-%d %H:%M:%S")
        days_left = 30 - (datetime.now() - join_date).days
        response += f"<a href='tg://user?id={user_id}'>Kullanıcı</a>: {days_left} gün kaldı\n"
    await bot.send_message(admin_id, response, parse_mode="HTML")

async def on_startup():
    scheduler.add_job(check_users, "interval", hours=1)
    scheduler.start()

async def main():
    logging.basicConfig(level=logging.INFO)
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
