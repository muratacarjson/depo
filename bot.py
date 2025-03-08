import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import time
from datetime import datetime, timedelta
import sqlite3
import threading



TOKEN = '7818517016:AAGiG3hsYcvB2YG7L5Q0zPOsCsyokE87KYc'

# Veritabanı bağlantısı
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER, chat_id INTEGER, join_date TEXT)''')
    conn.commit()
    conn.close()

# Yeni üye katıldığında
def welcome(update, context):
    chat_id = update.message.chat_id
    for new_member in update.message.new_chat_members:
        user_id = new_member.id

        # Veritabanına kaydet
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        join_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute("INSERT INTO users (user_id, chat_id, join_date) VALUES (?, ?, ?)",
                 (user_id, chat_id, join_date))
        conn.commit()
        conn.close()

        update.message.reply_text(f"Hoş geldin {new_member.full_name}! 30 günün başladı.")

# Kalan süreyi kontrol etme (manuel komut)
def check_time(update, context):
    chat_id = update.message.chat_id
    message = check_and_kick_users(context, chat_id)
    update.message.reply_text(message)

# Otomatik kontrol fonksiyonu
def check_and_kick_users(context, chat_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    c.execute("SELECT user_id, join_date FROM users WHERE chat_id = ?", (chat_id,))
    users = c.fetchall()

    message = "Kullanıcıların kalan süreleri:\n"
    current_time = datetime.now()
    users_to_remove = []

    for user_id, join_date in users:
        join_datetime = datetime.strptime(join_date, '%Y-%m-%d %H:%M:%S')
        expiry_date = join_datetime + timedelta(days=30)
        remaining_time = expiry_date - current_time

        try:
            member = context.bot.get_chat_member(chat_id, user_id)
            user_name = member.user.full_name
        except:
            user_name = f"User_{user_id}"

        if remaining_time.total_seconds() <= 0:
            try:
                context.bot.kick_chat_member(chat_id, user_id)
                users_to_remove.append((user_id, chat_id))
                message += f"{user_name} - Süresi doldu ve gruptan atıldı\n"
            except:
                message += f"{user_name} - Atılamadı (yetki hatası)\n"
        else:
            days_left = remaining_time.days
            hours_left = remaining_time.seconds // 3600
            message += f"{user_name} - {days_left} gün {hours_left} saat kaldı\n"

    # Süresi dolanları veritabanından sil
    for user_id, chat_id in users_to_remove:
        c.execute("DELETE FROM users WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))

    conn.commit()
    conn.close()
    return message

# Otomatik kontrol döngüsü
def auto_check(context):
    while True:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT DISTINCT chat_id FROM users")
        chat_ids = c.fetchall()
        conn.close()

        for (chat_id,) in chat_ids:
            check_and_kick_users(context, chat_id)

        # Her 1 saatte bir kontrol et (3600 saniye)
        time.sleep(3600)

# Botu başlat
def main():
    init_db()
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Handler'ları ekle
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, welcome))
    dp.add_handler(CommandHandler("zaman", check_time))

    # Otomatik kontrolü ayrı bir thread'de başlat
    context = updater.job_queue
    threading.Thread(target=auto_check, args=(context,), daemon=True).start()

    # Botu çalıştır
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
