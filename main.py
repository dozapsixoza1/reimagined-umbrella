"""
TK Fame List — Telegram авторизационный бот
==========================================

Установка:
    pip install pytelegrambotapi flask flask-cors

Запуск:
    python bot.py

Переменные (отредактируй прямо здесь или вынеси в .env):
    BOT_TOKEN   — токен от @BotFather
    SITE_URL    — URL твоего сайта (для CORS)
    SECRET_KEY  — любая случайная строка
"""

import telebot
import secrets
import time
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS

# ─── НАСТРОЙКИ ────────────────────────────────────────────
BOT_TOKEN  = "8741779031:AAGN82KPg5Ad4SXFH40ssjleaY48_c9nGQc"   # ← вставь токен
SITE_URL   = "https://tkfamelist.vercel.app"     # ← URL сайта (или * для теста)
SECRET_KEY = "o5yRF3cq42Uu4s6dV5ZvOQ_DCzWkkMYv7B2c22U4Pro"
# ──────────────────────────────────────────────────────────

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
CORS(app, origins=[SITE_URL, "http://localhost", "http://127.0.0.1"])

# Хранилище токенов: { token: { user_data, expires_at } }
token_store = {}
TOKEN_TTL = 300  # 5 минут

def clean_expired():
    """Чистим просроченные токены каждые 60 сек"""
    while True:
        now = time.time()
        expired = [t for t, v in token_store.items() if v["expires_at"] < now]
        for t in expired:
            del token_store[t]
        time.sleep(60)

threading.Thread(target=clean_expired, daemon=True).start()


# ─── БОТ ──────────────────────────────────────────────────

@bot.message_handler(commands=["start"])
def cmd_start(message):
    user = message.from_user

    # Генерируем уникальный токен
    token = secrets.token_urlsafe(24)
    token_store[token] = {
        "expires_at": time.time() + TOKEN_TTL,
        "user": {
            "id":         user.id,
            "username":   (user.username or f"user{user.id}").lower(),
            "first_name": user.first_name or user.username or "Пользователь",
            "photo_url":  None   # Фото профиля TG не выдаёт напрямую без доп. запроса
        }
    }

    text = (
        f"👋 Привет, <b>{user.first_name}</b>!\n\n"
        f"🔑 Твой одноразовый токен для входа на <b>TK Fame List</b>:\n\n"
        f"<code>{token}</code>\n\n"
        f"📋 <b>Скопируй токен</b> (нажми на него) и вставь на сайте.\n"
        f"⏳ Токен действует <b>5 минут</b> и сгорает после использования."
    )

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="HTML"
    )


@bot.message_handler(commands=["help"])
def cmd_help(message):
    bot.send_message(
        message.chat.id,
        "📖 <b>TK Fame List Bot</b>\n\n"
        "Команды:\n"
        "/start — получить токен для входа на сайт\n"
        "/help — эта справка",
        parse_mode="HTML"
    )


@bot.message_handler(func=lambda m: True)
def fallback(message):
    bot.send_message(
        message.chat.id,
        "Напиши /start чтобы получить токен для входа 🔑"
    )


# ─── FLASK API ────────────────────────────────────────────

@app.route("/verify-token", methods=["POST"])
def verify_token():
    """
    Сайт отправляет: { "token": "..." }
    Возвращаем:      { "ok": true, "user": { id, username, first_name } }
                  или { "ok": false, "error": "..." }
    """
    data = request.get_json(silent=True)
    if not data or "token" not in data:
        return jsonify({"ok": False, "error": "No token provided"}), 400

    token = data["token"].strip()
    entry = token_store.get(token)

    if not entry:
        return jsonify({"ok": False, "error": "Invalid token"}), 401

    if entry["expires_at"] < time.time():
        del token_store[token]
        return jsonify({"ok": False, "error": "Token expired"}), 401

    # Токен одноразовый — удаляем после использования
    user_data = entry["user"]
    del token_store[token]

    return jsonify({"ok": True, "user": user_data})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "tokens_active": len(token_store)})


# ─── ЗАПУСК ───────────────────────────────────────────────

if __name__ == "__main__":
    print("🤖 Бот запущен...")
    print(f"🌐 API слушает на порту 5000")
    print(f"📡 CORS разрешён для: {SITE_URL}")

    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=5000, debug=False),
        daemon=True
    )
    flask_thread.start()

    # Запускаем бота (polling)
    print("✅ Готов принимать команды!")
    bot.infinity_polling(timeout=30, long_polling_timeout=15)
