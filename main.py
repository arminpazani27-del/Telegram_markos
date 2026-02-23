import telebot
import os
import random
import json
import difflib

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
    if not group: return False
    if group.get("locked"): return False
    return group.get("active", False)

def ensure_group_registered(message):
    if message.chat.type not in ["group", "supergroup"]:
        return
    data = load_data()
    if str(message.chat.id) not in data["groups"]:
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
            "برای فعالسازی به پیوی من برو و رمز را وارد کن."
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
    ensure_group_registered(message)
    if message.chat.type in ["group","supergroup"] and not is_group_active(message.chat.id):
        return
    try:
        key = message.text.split(" ",1)[1]
        pending_teach[message.from_user.id] = {
            "key": key,
            "reply_required": True if message.reply_to_message else False
        }
        bot.reply_to(message, "پاسخ رو بفرست.")
    except:
        pass

@bot.message_handler(commands=['kosbego'])
def kosbego_cmd(message):
    ensure_group_registered(message)
    if message.chat.type in ["group","supergroup"] and not is_group_active(message.chat.id):
        return
    bot.send_message(message.chat.id, "ربات می‌تواند پاسخ خودکار بدهد، ریپلای کند، استیکر و ویس بفرستد، کلمات را یاد بگیرد و کامند /work روی دو نفر رندوم اجرا شود.")

@bot.message_handler(commands=['work'])
def work_cmd(message):
    ensure_group_registered(message)
    if message.chat.type in ["group","supergroup"] and not is_group_active(message.chat.id):
        return
    chat = message.chat
    try:
        members = [m.user.id for m in bot.get_chat_administrators(chat.id)]
        users = [u for u in members if u != message.from_user.id]
        if len(users)>=2:
            selected = random.sample(users,2)
            bot.send_message(chat.id,f"@{selected[0]} رابرت بیا کارت دارم",reply_to_message_id=message.message_id)
            bot.send_message(chat.id,f"@{selected[1]} این گوتم با خودت بیار",reply_to_message_id=message.message_id)
    except:
        bot.send_message(chat.id,"نمیتونم دو نفر رندوم پیدا کنم.")

@bot.message_handler(content_types=['text','voice','sticker','video'])
def handle_all(message):
    ensure_group_registered(message)
    if message.chat.type in ["group","supergroup"] and not is_group_active(message.chat.id):
        return

    data = load_data()
    user_id = message.from_user.id

    if user_id in pending_teach:
        teach_data = pending_teach[user_id]
        key = teach_data["key"]
        reply_required = teach_data["reply_required"]

        if message.content_type == "text":
            data["learned"][key] = {
                "type":"text",
                "content": message.text,
                "reply_required": reply_required
            }
        save_data(data)
        del pending_teach[user_id]
        bot.reply_to(message,"یاد گرفتم.")
        return

    if message.content_type=="text":
        text = message.text
        if "گم شو" in text:
            if message.reply_to_message:
                bot.send_message(message.chat.id,"سیهدیر",reply_to_message_id=message.reply_to_message.message_id)
            else:
                bot.reply_to(message,"سیهدیر")

        if "مارکوس" in text:
            bot.send_message(message.chat.id,"ندع رابرت")
        elif "دوست دارم مارکوس" in text:
            bot.send_message(message.chat.id,"اگه پشه بودم باز دوسم داشتی؟")
        elif "مارکوس ماشینت چیشده" in text:
            bot.send_message(message.chat.id,"من اشتباهی تو باک تویوتا کم چرپ یک درصد ریختم")
        elif "چه فرقی داره" in text:
            bot.send_message(message.chat.id,"از شیر پر چرپ ۳ درصد بهتره")

        if data["learned"]:
            closest = difflib.get_close_matches(text,data["learned"].keys(),n=1,cutoff=0.6)
            if closest:
                item = data["learned"][closest[0]]
                if item.get("reply_required") and not message.reply_to_message:
                    return
                if item["type"]=="text":
                    if message.reply_to_message:
                        bot.send_message(message.chat.id,item["content"],reply_to_message_id=message.reply_to_message.message_id)
                    else:
                        bot.reply_to(message,item["content"])

bot.polling(non_stop=True)
