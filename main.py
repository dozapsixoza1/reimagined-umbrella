"""
TK Fame List — Telegram бот (Firestore версия)
===============================================

Установка:
    pip install pytelegrambotapi firebase-admin

Запуск:
    python bot.py

Положи serviceAccountKey.json рядом с этим файлом.
"""

import telebot
import secrets
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone

# ─── НАСТРОЙКИ ────────────────────────────────────────────
BOT_TOKEN = "8741779031:AAGN82KPg5Ad4SXFH40ssjleaY48_c9nGQc"   # ← вставь токен от @BotFather
# ──────────────────────────────────────────────────────────

# Подключаем Firebase
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

bot = telebot.TeleBot(BOT_TOKEN)


# ─── /start и /token ──────────────────────────────────────

@bot.message_handler(commands=["start", "token"])
def cmd_token(message):
    user = message.from_user
    token = secrets.token_urlsafe(24)

    # Записываем токен прямо в Firestore — сайт его найдёт
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
    print("✅ Бот запущен! Ожидаю команды...")
    bot.infinity_polling(timeout=30, long_polling_timeout=15)
