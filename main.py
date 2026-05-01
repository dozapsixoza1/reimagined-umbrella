import telebot
import secrets
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone
import os
import json
import time

# ─── НАСТРОЙКИ ────────────────────────────────────────────
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TOKEN")
# ──────────────────────────────────────────────────────────

# Подключаем Firebase из переменной окружения
firebase_key_json = os.environ.get("FIREBASE_KEY")
if not firebase_key_json:
    raise Exception("❌ Переменная FIREBASE_KEY не найдена!")

firebase_key_dict = json.loads(firebase_key_json)
cred = credentials.Certificate(firebase_key_dict)
firebase_admin.initialize_app(cred)
db = firestore.client()

bot = telebot.TeleBot(BOT_TOKEN)

# Сбрасываем вебхук чтобы не было конфликтов
bot.remove_webhook()
time.sleep(2)


# ─── /start и /token ──────────────────────────────────────

@bot.message_handler(commands=["start", "token"])
def cmd_token(message):
    user = message.from_user
    token = secrets.token_urlsafe(24)

    db.collection("tokens").document(token).set({
        "tgId":      str(user.id),
        "username":  (user.username or f"user{user.id}").lower(),
        "name":      user.first_name or user.username or "Пользователь",
        "used":      False,
        "createdAt": datetime.now(timezone.utc)
    })

    bot.send_message(
        message.chat.id,
        f"👋 Привет, <b>{user.first_name}</b>!\n\n"
        f"🔑 Твой одноразовый токен для входа на <b>TK Fame List</b>:\n\n"
        f"<code>{token}</code>\n\n"
        f"📋 Нажми на токен чтобы скопировать, затем вставь на сайте.\n"
        f"⏳ Токен действует <b>10 минут</b> и сгорает после использования.",
        parse_mode="HTML"
    )


# ─── /help ────────────────────────────────────────────────

@bot.message_handler(commands=["help"])
def cmd_help(message):
    bot.send_message(
        message.chat.id,
        "📖 <b>TK Fame List Bot</b>\n\n"
        "Команды:\n"
        "/token — получить токен для входа на сайт\n"
        "/help — эта справка",
        parse_mode="HTML"
    )


# ─── Всё остальное ────────────────────────────────────────

@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.send_message(
        message.chat.id,
        "Напиши /token чтобы получить токен для входа 🔑"
    )


# ─── ЗАПУСК ───────────────────────────────────────────────

if __name__ == "__main__":
    print("✅ Бот запущен!")
    bot.infinity_polling(
        timeout=30,
        long_polling_timeout=15,
        allowed_updates=["message"]
    )
