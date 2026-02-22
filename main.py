import telebot
import os
import random
import json
import subprocess

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

DATA_FILE = "data.json"

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({
            "admins": [],
            "mode": "text",
            "auto_extract": False,
            "learned": {},
            "stickers": []
        }, f)

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def is_admin(user_id):
    data = load_data()
    return user_id in data["admins"]

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "ربات فعاله.")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(message, "/teach /work /setmode /addadmin /deladmin /setautoextract")

@bot.message_handler(commands=['addadmin'])
def add_admin(message):
    if not is_admin(message.from_user.id) and len(load_data()["admins"]) > 0:
        return
    try:
        user_id = int(message.text.split()[1])
        data = load_data()
        if user_id not in data["admins"]:
            data["admins"].append(user_id)
            save_data(data)
            bot.reply_to(message, "ادمین اضافه شد.")
    except:
        pass

@bot.message_handler(commands=['deladmin'])
def del_admin(message):
    if not is_admin(message.from_user.id):
        return
    try:
        user_id = int(message.text.split()[1])
        data = load_data()
        if user_id in data["admins"]:
            data["admins"].remove(user_id)
            save_data(data)
            bot.reply_to(message, "ادمین حذف شد.")
    except:
        pass

@bot.message_handler(commands=['setmode'])
def set_mode(message):
    if not is_admin(message.from_user.id):
        return
    try:
        mode = message.text.split()[1]
        if mode in ["text", "voice"]:
            data = load_data()
            data["mode"] = mode
            save_data(data)
            bot.reply_to(message, "حالت تنظیم شد.")
    except:
        pass

@bot.message_handler(commands=['setautoextract'])
def set_auto(message):
    if not is_admin(message.from_user.id):
        return
    try:
        state = message.text.split()[1]
        data = load_data()
        data["auto_extract"] = True if state == "on" else False
        save_data(data)
        bot.reply_to(message, "تنظیم شد.")
    except:
        pass

pending_teach = {}

@bot.message_handler(commands=['teach'])
def teach(message):
    try:
        key = message.text.split(" ", 1)[1]
        pending_teach[message.from_user.id] = key
        bot.reply_to(message, "پاسخ رو بفرست.")
    except:
        pass

@bot.message_handler(content_types=['text', 'voice', 'video', 'sticker'])
def handle_all(message):
    data = load_data()
    user_id = message.from_user.id

    if user_id in pending_teach:
        key = pending_teach[user_id]
        if message.content_type == "text":
            data["learned"][key] = {"type": "text", "content": message.text}
        elif message.content_type == "voice":
            file_info = bot.get_file(message.voice.file_id)
            downloaded = bot.download_file(file_info.file_path)
            path = f"{key}.ogg"
            with open(path, "wb") as f:
                f.write(downloaded)
            data["learned"][key] = {"type": "voice", "content": path}
        save_data(data)
        del pending_teach[user_id]
        bot.reply_to(message, "یاد گرفتم.")
        return

    if message.text:
        text = message.text

        if message.chat.type in ["group", "supergroup"]:
            if text == "/work":
                members = bot.get_chat_administrators(message.chat.id)
                users = [m.user.id for m in members]
                if len(users) >= 2:
                    u1, u2 = random.sample(users, 2)
                    bot.send_message(message.chat.id, "رابرت بیا کارت دارم", reply_to_message_id=message.message_id)
                    bot.send_message(message.chat.id, "این گوتم با خودت بیار", reply_to_message_id=message.message_id)
                return

        if "مارکوس" in text:
            bot.reply_to(message, "ندع رابرت")
        elif "دوست دارم مارکوس" in text:
            bot.reply_to(message, "اگه پشه بودم باز دوسم داشتی؟")
        elif "مارکوس ماشینت چیشده" in text:
            bot.reply_to(message, "من اشتباهی تو باک تویوتا کم چرپ ریختم")
        elif "چه فرقی داره" in text:
            bot.reply_to(message, "از شیر پر چرپ بهتره")
        elif "گم شو" in text:
            bot.reply_to(message, "سیهدیر")

        if text in data["learned"]:
            item = data["learned"][text]
            if item["type"] == "text":
                bot.reply_to(message, item["content"])
            elif item["type"] == "voice" and data["mode"] == "voice":
                with open(item["content"], "rb") as v:
                    bot.send_voice(message.chat.id, v, reply_to_message_id=message.message_id)

        if data["stickers"]:
            bot.send_sticker(message.chat.id, random.choice(data["stickers"]))

    if message.content_type == "sticker":
        if message.chat.type == "private":
            data["stickers"].append(message.sticker.file_id)
            save_data(data)

    if message.content_type == "video":
        file_info = bot.get_file(message.video.file_id)
        downloaded = bot.download_file(file_info.file_path)
        video_path = "video.mp4"
        with open(video_path, "wb") as f:
            f.write(downloaded)

        audio_path = "audio.ogg"
        subprocess.run(["ffmpeg", "-i", video_path, "-vn", "-acodec", "copy", audio_path])

        with open(audio_path, "rb") as a:
            bot.send_voice(message.chat.id, a)

bot.polling(non_stop=True)
