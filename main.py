import json
import telebot
import secrets
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone
import os
import time

# ─── НАСТРОЙКИ ────────────────────────────────────────────
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TOKEN")
if not BOT_TOKEN:
    print("❌ Ошибка: TOKEN не установлен в переменных окружения!")
    exit(1)

# ─── ПОДКЛЮЧЕНИЕ FIREBASE ─────────────────────────────────
try:
    firebase_json = os.environ.get("FIREBASE_KEY_JSON")
    if not firebase_json:
        print("❌ FIREBASE_KEY_JSON не установлен в переменных окружения!")
        exit(1)
    cred_dict = json.loads(firebase_json)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print(f"✅ Firebase подключен! project_id={cred_dict.get('project_id')}", flush=True)
except Exception as e:
    print(f"❌ Ошибка подключения Firebase: {e}", flush=True)
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

bot.remove_webhook()
time.sleep(1)

# ─── КОМАНДЫ БОТА ─────────────────────────────────────────

@bot.message_handler(commands=["start", "token"])
def cmd_token(message):
    print("🔵 /token получен", flush=True)
    user = message.from_user
    token = secrets.token_urlsafe(24)

    try:
        db.collection("tokens").document(token).set({
            "tgId":      str(user.id),
            "username":  (user.username or f"user{user.id}").lower(),
            "name":      user.first_name or user.username or "Пользователь",
            "used":      False,
            "createdAt": datetime.now(timezone.utc)
        })
        print(f"✅ Токен {token} записан в Firestore для {user.id}", flush=True)
    except Exception as e:
        print(f"❌ ОШИБКА ЗАПИСИ В FIRESTORE: {e}", flush=True)
        bot.send_message(message.chat.id, "⚠️ Ошибка сервера, попробуй позже")
        return

    bot.send_message(
        message.chat.id,
        f"👋 Привет, <b>{user.first_name}</b>!\n\n"
        f"🔑 Твой одноразовый токен для входа на <b>TK Fame List</b>:\n\n"
        f"<code>{token}</code>\n\n"
        f"📋 Нажми на токен чтобы скопировать, затем вставь на сайте.\n"
        f"⏳ Токен действует <b>10 минут</b> и сгорает после использования.",
        parse_mode="HTML"
    )

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

@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.send_message(
        message.chat.id,
        "Напиши /token чтобы получить токен для входа 🔑"
    )

# ─── ЗАПУСК ───────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Бот запускается...", flush=True)
    bot.infinity_polling(
        timeout=30,
        long_polling_timeout=15,
        allowed_updates=["message"]
    )
