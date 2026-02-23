import telebot
import os
import random
import json
import difflib
import subprocess

TOKEN = os.getenv("BOT_TOKEN")
PASSWORD = os.getenv("BOT_PASSWORD")

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "data.json"

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({
            "admins": [],
            "mode": "text",
            "auto_extract": False,
            "learned": {},
            "stickers": [],
            "groups": {}
        }, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

pending_teach = {}
pending_group_auth = {}

def is_group_active(chat_id):
    data = load_data()
    group = data["groups"].get(str(chat_id))
    return group and group.get("active") == True

@bot.message_handler(content_types=['new_chat_members'])
def bot_added(message):
    for member in message.new_chat_members:
        if member.id == bot.get_me().id:
            data = load_data()
            data["groups"][str(message.chat.id)] = {
                "active": False,
                "owner": message.from_user.id,
                "attempts": 0,
                "locked": False
            }
            save_data(data)

            pending_group_auth[message.from_user.id] = message.chat.id

            bot.send_message(
                message.chat.id,
                "برای فعالسازی ربات، به پیوی من برو و رمز را وارد کن."
            )

@bot.message_handler(func=lambda m: m.chat.type == "private")
def private_auth(message):
    user_id = message.from_user.id
    data = load_data()

    if user_id in pending_group_auth:
        group_id = pending_group_auth[user_id]
        group = data["groups"].get(str(group_id))

        if group["locked"]:
            bot.reply_to(message, "این گروه قفل شده.")
            return

        if message.text == PASSWORD:
            group["active"] = True
            save_data(data)
            del pending_group_auth[user_id]
            bot.reply_to(message, "ربات فعال شد.")
            bot.send_message(group_id, "ربات فعال شد ✅")
        else:
            group["attempts"] += 1
            if group["attempts"] >= 3:
                group["locked"] = True
                bot.reply_to(message, "۳ بار اشتباه. گروه قفل شد.")
                bot.send_message(group_id, "گروه قفل شد ❌")
            save_data(data)
        return

@bot.message_handler(commands=['teach'])
def teach(message):
    if message.chat.type in ["group", "supergroup"]:
        if not is_group_active(message.chat.id):
            return
    try:
        key = message.text.split(" ", 1)[1]
        pending_teach[message.from_user.id] = {
            "key": key,
            "reply_required": True if message.reply_to_message else False
        }
        bot.reply_to(message, "پاسخ رو بفرست.")
    except:
        pass

@bot.message_handler(content_types=['text', 'voice', 'video', 'sticker'])
def handle_all(message):
    data = load_data()

    if message.chat.type in ["group", "supergroup"]:
        if not is_group_active(message.chat.id):
            return

    user_id = message.from_user.id

    if user_id in pending_teach:
        teach_data = pending_teach[user_id]
        key = teach_data["key"]
        reply_required = teach_data["reply_required"]

        if message.content_type == "text":
            data["learned"][key] = {
                "type": "text",
                "content": message.text,
                "reply_required": reply_required
            }

        save_data(data)
        del pending_teach[user_id]
        bot.reply_to(message, "یاد گرفتم.")
        return

    if message.content_type == "text":
        text = message.text

        if "گم شو" in text:
            if message.reply_to_message:
                bot.send_message(
                    message.chat.id,
                    "سیهدیر",
                    reply_to_message_id=message.reply_to_message.message_id
                )
            else:
                bot.reply_to(message, "سیهدیر")

        if data["learned"]:
            closest = difflib.get_close_matches(text, data["learned"].keys(), n=1, cutoff=0.6)
            if closest:
                item = data["learned"][closest[0]]
                if item.get("reply_required") and not message.reply_to_message:
                    return
                if item["type"] == "text":
                    if message.reply_to_message:
                        bot.send_message(
                            message.chat.id,
                            item["content"],
                            reply_to_message_id=message.reply_to_message.message_id
                        )
                    else:
                        bot.reply_to(message, item["content"])

bot.polling(non_stop=True)
