import json
import telebot
import firebase_admin
from firebase_admin import credentials, firestore, auth
from datetime import datetime, timezone
import os
import time
import threading

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

# username владельца сайта — должен совпадать с SA в index.html
SA_USERNAME = "psychokaratel"

def ensure_owner_role(uid, un):
    """Если это владелец сайта — гарантируем ему role=admin в Firestore.
    Admin SDK обходит Security Rules, так что это безопасно делать только тут."""
    if un != SA_USERNAME:
        return
    try:
        doc_ref = db.collection("users").document(uid)
        snap = doc_ref.get()
        if snap.exists:
            if snap.to_dict().get("role") != "admin":
                doc_ref.update({"role": "admin"})
                print(f"👑 Роль владельца восстановлена для {uid}", flush=True)
        # если документа ещё нет — сайт создаст его сам при первом входе
        # с role='user', и следующий /token поднимет его до admin
    except Exception as e:
        print(f"❌ Ошибка ensure_owner_role: {e}", flush=True)

# ─── КОМАНДЫ БОТА ─────────────────────────────────────────

@bot.message_handler(commands=["start", "token"])
def cmd_token(message):
    print("🔵 /token получен", flush=True)
    user = message.from_user

    uid = f"tg_{user.id}"
    un = (user.username or f"user{user.id}").lower()
    name = user.first_name or user.username or "Пользователь"

    ensure_owner_role(uid, un)

    try:
        # Реальный Firebase Auth Custom Token — подписан ключом сервисного
        # аккаунта, его нельзя подделать. Действует 1 час.
        custom_token = auth.create_custom_token(uid, {
            "un": un,
            "name": name,
            "tgId": str(user.id),
        })
        token_str = custom_token.decode("utf-8") if isinstance(custom_token, bytes) else custom_token
        print(f"✅ Custom token выпущен для uid={uid}", flush=True)
    except Exception as e:
        print(f"❌ ОШИБКА ВЫПУСКА ТОКЕНА: {e}", flush=True)
        bot.send_message(message.chat.id, "⚠️ Ошибка сервера, попробуй позже")
        return

    bot.send_message(
        message.chat.id,
        f"👋 Привет, <b>{name}</b>!\n\n"
        f"🔑 Твой токен для входа на <b>TK Fame List</b>:\n\n"
        f"<code>{token_str}</code>\n\n"
        f"📋 Нажми на токен чтобы скопировать, затем вставь на сайте.\n"
        f"⏳ Токен действует <b>1 час</b>.",
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

# ─── PUSH-УВЕДОМЛЕНИЯ ЧЕРЕЗ САЙТ ────────────────────────────
# Сайт пишет документы в коллекцию pushQueue: {uid, text, ts}
# uid имеет формат "tg_<telegram_id>", так что chat_id достаём прямо из него.
# Этот поток раз в PUSH_POLL_SECONDS проверяет очередь, шлёт сообщение и удаляет запись.

PUSH_POLL_SECONDS = 12

def push_worker():
    print("📬 Push-воркер запущен", flush=True)
    while True:
        try:
            docs = list(db.collection("pushQueue").limit(50).stream())
            for doc in docs:
                data = doc.to_dict() or {}
                uid = data.get("uid", "")
                text = data.get("text", "")
                if uid.startswith("tg_") and text:
                    try:
                        chat_id = int(uid.replace("tg_", ""))
                        bot.send_message(chat_id, text, parse_mode="HTML")
                    except Exception as send_err:
                        print(f"⚠️ Не удалось отправить push для {uid}: {send_err}", flush=True)
                doc.reference.delete()
        except Exception as e:
            print(f"❌ Ошибка push_worker: {e}", flush=True)
        time.sleep(PUSH_POLL_SECONDS)

# ─── ЗАПУСК ───────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Бот запускается...", flush=True)
    threading.Thread(target=push_worker, daemon=True).start()
    bot.infinity_polling(
        timeout=30,
        long_polling_timeout=15,
        allowed_updates=["message"]
    )
