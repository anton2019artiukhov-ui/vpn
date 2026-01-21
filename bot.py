import telebot
import json
import os
import threading
import time
from datetime import datetime, timedelta
from telebot import types

# ================= ПАРАМЕТРЫ =================
TOKEN = '7967689331:AAFC6El9N8B-zym_uW8jysP4IfelwGznM90'
ADMIN_ID = 2133249292
ADMIN_USERNAME = "@shdjflgldl"
DB_FILE = 'database.json'
# =============================================

bot = telebot.TeleBot(TOKEN)

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "users": {}, 
        "vpn_tokens": [], 
        "channels": [], 
        "settings": {
            "next_user_number": 1,
            "prices": {"1": 300, "3": 855, "6": 1530, "12": 2520}
        }
    }

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

# --- Проверка подписки ---
def is_subscribed(user_id):
    if user_id == ADMIN_ID: return True
    for channel_id in db.get("channels", []):
        try:
            status = bot.get_chat_member(channel_id, user_id).status
            if status in ['left', 'kicked']: return False
        except Exception: continue
    return True

def get_sub_keyboard():
    markup = types.InlineKeyboardMarkup()
    for channel_id in db.get("channels", []):
        try:
            chat = bot.get_chat(channel_id)
            link = chat.invite_link or f"https://t.me/{chat.username}"
            markup.add(types.InlineKeyboardButton(text=f"Подписаться на {chat.title}", url=link))
        except: continue
    markup.add(types.InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subs"))
    return markup

# --- Инструкция ---
INSTRUCTION = (
    "📖 **Инструкция по подключению:**\n\n"
    "1. **Установите приложение**: Скачайте **Amnezia VPN** в App Store или Google Play.\n"
    "2. **Скопируйте ваш ключ**: Нажмите на ключ (текст выше), он скопируется автоматически.\n"
    "3. **Настройте сервер**: В приложении выберите «Добавить сервер» или нажмите «+».\n"
    "4. **Импорт**: Выберите «Настроить вручную» -> «Вставить из буфера обмена».\n"
    "5. **Подключение**: Нажмите кнопку подключения. Ваш сервер в Мадриде готов! 🇪🇸"
)

# --- Клавиатуры ---
def main_kb(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚀 Попробовать (1 день)", "💳 Купить подписку")
    markup.add("👤 Профиль", "📝 Инструкция")
    markup.add("🎁 Реферальная программа", "🆘 Поддержка")
    if int(uid) == ADMIN_ID: markup.add("⚙️ Админ-панель")
    return markup

# --- Фоновая проверка ---
def expiration_checker():
    while True:
        now = datetime.now()
        changed = False
        for uid, u in list(db["users"].items()):
            if not u.get("expiry_date"): continue
            exp = datetime.strptime(u["expiry_date"], "%Y-%m-%d %H:%M")
            rem = exp - now
            
            # Уведомления за 7 дней и 1 день
            if timedelta(days=6) < rem <= timedelta(days=7) and not u.get("n7"):
                try: bot.send_message(uid, "🔔 Здравствуйте! Ваша подписка истекает через неделю."); u["n7"] = True; changed = True
                except: pass
            if timedelta(hours=23) < rem <= timedelta(days=1) and not u.get("n1"):
                try: bot.send_message(uid, "🔔 Внимание! До конца подписки осталось менее 24 часов."); u["n1"] = True; changed = True
                except: pass
            
            # Возврат ключа через 24 часа после конца
            if now > exp + timedelta(hours=24) and not u.get("n_admin"):
                if u.get("token"):
                    db["vpn_tokens"].append(u["token"])
                    u["token"] = None
                try: bot.send_message(ADMIN_ID, f"🔴 Ключ пользователя №{u['number']} изъят (прошло 24ч после конца)."); u["n_admin"] = True; changed = True
                except: pass
        if changed: save_db(db)
        time.sleep(1200)

# ================= ОБРАБОТЧИКИ ПОЛЬЗОВАТЕЛЕЙ =================

@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
    if not is_subscribed(message.from_user.id):
        return bot.send_message(message.chat.id, "👋 Добро пожаловать! Для доступа к боту подпишитесь на наши каналы:", reply_markup=get_sub_keyboard())

    if uid not in db["users"]:
        ref = message.text.split()[1] if len(message.text.split()) > 1 else None
        db["users"][uid] = {
            "number": db["settings"]["next_user_number"], "balance_days": 0,
            "trial_used": False, "expiry_date": None, "token": None, "discount": 0,
            "n7": False, "n1": False, "n_admin": False
        }
        db["settings"]["next_user_number"] += 1
        if ref and ref in db["users"] and ref != uid:
            db["users"][ref]["balance_days"] += 3
            bot.send_message(ref, "🎁 Поздравляем! Друг активировал бота, вам начислено 3 дня!")
        save_db(db)
    
    bot.send_message(message.chat.id, f"🇪🇸 **Siesta VPN приветствует Вас!**\nВаш номер пользователя: **№{db['users'][uid]['number']}**.", 
                     parse_mode="Markdown", reply_markup=main_kb(uid))

@bot.callback_query_handler(func=lambda c: c.data == "check_subs")
def check_subs_btn(call):
    if is_subscribed(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Вы подписались не на все каналы!", show_alert=True)

@bot.message_handler(func=lambda m: m.text == "🚀 Попробовать (1 день)")
def trial(message):
    uid = str(message.from_user.id)
    u = db["users"][uid]
    if u["trial_used"]: return bot.send_message(message.chat.id, "❌ Пробный период уже был использован вами ранее.")
    if not db["vpn_tokens"]: return bot.send_message(message.chat.id, "😔 К сожалению, свободные ключи закончились. Напишите в поддержку.")
    
    tk = db["vpn_tokens"].pop(0)
    u.update({"trial_used": True, "token": tk, "expiry_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"), "n7":True, "n1":True})
    save_db(db)
    bot.send_message(message.chat.id, f"✅ Ваш бесплатный доступ на 24 часа:\n\n`{tk}`", parse_mode="Markdown")
    bot.send_message(message.chat.id, INSTRUCTION, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💳 Купить подписку")
def buy_menu(message):
    uid = str(message.from_user.id)
    d = db["users"][uid].get("discount", 0)
    p = db["settings"]["prices"]
    def calc(val): return int(val * (1 - d/100))
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"1 месяц — {calc(p['1'])}₽", callback_data="buy_1"))
    markup.add(types.InlineKeyboardButton(f"3 месяца — {calc(p['3'])}₽", callback_data="buy_3"))
    markup.add(types.InlineKeyboardButton(f"6 месяцев — {calc(p['6'])}₽", callback_data="buy_6"))
    markup.add(types.InlineKeyboardButton(f"1 год — {calc(p['12'])}₽", callback_data="buy_12"))
    
    text = "💳 **Выберите тарифный план:**\n\nПри каждой покупке вы получаете +2 дня в подарок!"
    if d > 0: text += f"\n\n🔥 Ваша личная скидка: **{d}%**"
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def process_buy(call):
    uid = str(call.from_user.id)
    months = int(call.data.split("_")[1])
    days = (months * 30) + 2
    u = db["users"][uid]
    
    now = datetime.now()
    start_dt = max(now, datetime.strptime(u["expiry_date"], "%Y-%m-%d %H:%M")) if u["expiry_date"] else now
    if not u["token"] and db["vpn_tokens"]: u["token"] = db["vpn_tokens"].pop(0)
    
    u["expiry_date"] = (start_dt + timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
    u.update({"n7": False, "n1": False, "n_admin": False})
    save_db(db)
    
    bot.edit_message_text(f"✅ Успешно! Подписка активна до: **{u['expiry_date']}**\n\nВаш ключ:\n`{u['token']}`", 
                          call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    bot.send_message(call.message.chat.id, INSTRUCTION, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(message):
    uid = str(message.from_user.id)
    u = db["users"][uid]
    markup = types.InlineKeyboardMarkup()
    if u["balance_days"] > 0:
        markup.add(types.InlineKeyboardButton("🎁 Активировать бонусы", callback_data="claim_bonus"))
    
    exp = u["expiry_date"] if u["expiry_date"] else "Нет активной подписки"
    text = (f"👤 **Ваш профиль №{u['number']}**\n\n"
            f"📅 Срок действия до: {exp}\n"
            f"🎁 Бонусные дни: {u['balance_days']} дн.\n"
            f"🔑 Ключ: `{u['token'] or 'Не получен'}`")
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "claim_bonus")
def claim_bonus(call):
    uid = str(call.from_user.id)
    u = db["users"][uid]
    if u["balance_days"] > 0:
        now = datetime.now()
        start_dt = max(now, datetime.strptime(u["expiry_date"], "%Y-%m-%d %H:%M")) if u["expiry_date"] else now
        u["expiry_date"] = (start_dt + timedelta(days=u["balance_days"])).strftime("%Y-%m-%d %H:%M")
        days = u["balance_days"]
        u["balance_days"] = 0
        save_db(db)
        bot.send_message(call.message.chat.id, f"✅ Бонусы ({days} дн.) добавлены к вашей подписке!")
        profile(call.message)

@bot.message_handler(func=lambda m: m.text == "🆘 Поддержка")
def support(message):
    bot.send_message(message.chat.id, f"🆘 По всем вопросам обращайтесь к администратору: {ADMIN_USERNAME}")

@bot.message_handler(func=lambda m: m.text == "📝 Инструкция")
def show_instr(message):
    bot.send_message(message.chat.id, INSTRUCTION, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🎁 Реферальная программа")
def referral(message):
    link = f"https://t.me/{bot.get_me().username}?start={message.from_user.id}"
    bot.send_message(message.chat.id, f"🎁 Приглашайте друзей и получайте **3 дня** VPN бесплатно!\n\nВаша ссылка:\n{link}")

# ================= АДМИН-ПАНЕЛЬ =================

@bot.message_handler(func=lambda m: m.text == "⚙️ Админ-панель" and m.from_user.id == ADMIN_ID)
def admin_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("➕ Ключи", callback_data="adm_add"),
               types.InlineKeyboardButton("🔑 Статус ключей", callback_data="adm_keystat"),
               types.InlineKeyboardButton("💰 Цены", callback_data="adm_prices"),
               types.InlineKeyboardButton("📊 Статистика", callback_data="adm_total"),
               types.InlineKeyboardButton("📢 Рассылка", callback_data="adm_mail"),
               types.InlineKeyboardButton("👤 Юзеры", callback_data="adm_users"),
               types.InlineKeyboardButton("📢 Каналы", callback_data="adm_chans"))
    bot.send_message(message.chat.id, "🛠 Меню администратора:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_"))
def admin_callbacks(call):
    if call.data == "adm_add":
        msg = bot.send_message(call.message.chat.id, "Отправьте ключи (каждый с новой строки):")
        bot.register_next_step_handler(msg, add_keys_proc)
    elif call.data == "adm_keystat":
        text = "🔑 **Занятые ключи:**\n"
        for uid, u in db["users"].items():
            if u["token"]:
                text += f"№{u['number']} (ID {uid}): до {u['expiry_date']}\n`{u['token']}`\n\n"
        text += f"**Свободных ключей в пуле:** {len(db['vpn_tokens'])}"
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    elif call.data == "adm_total":
        total = len(db["users"])
        active = sum(1 for u in db["users"].values() if u["expiry_date"] and datetime.strptime(u["expiry_date"], "%Y-%m-%d %H:%M") > datetime.now())
        bot.send_message(call.message.chat.id, f"📊 Всего юзеров: {total}\n⚡️ Активных: {active}")
    elif call.data == "adm_prices":
        markup = types.InlineKeyboardMarkup()
        for k, v in db["settings"]["prices"].items():
            markup.add(types.InlineKeyboardButton(f"{k} мес = {v}₽", callback_data=f"setpr_{k}"))
        bot.send_message(call.message.chat.id, "Выберите тариф для изменения цены:", reply_markup=markup)
    elif call.data == "adm_mail":
        msg = bot.send_message(call.message.chat.id, "Введите текст рассылки:")
        bot.register_next_step_handler(msg, mail_proc)
    elif call.data == "adm_users":
        msg = bot.send_message(call.message.chat.id, "Введите номер пользователя (№):")
        bot.register_next_step_handler(msg, user_manage_proc)
    elif call.data == "adm_chans":
        text = "📢 **Каналы:**\n" + "\n".join([str(c) for c in db["channels"]])
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Добавить", callback_data="chan_add"),
                   types.InlineKeyboardButton("🗑 Удалить", callback_data="chan_rem"))
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

# Вспомогательные функции админа
def add_keys_proc(message):
    keys = message.text.split('\n')
    db["vpn_tokens"].extend([k.strip() for k in keys if k.strip()])
    save_db(db); bot.send_message(message.chat.id, f"✅ Добавлено: {len(keys)}")

def mail_proc(message):
    count = 0
    for uid in db["users"]:
        try: bot.send_message(uid, message.text); count += 1
        except: pass
    bot.send_message(message.chat.id, f"✅ Рассылка завершена ({count} чел.)")

@bot.callback_query_handler(func=lambda c: c.data.startswith("setpr_"))
def set_price_call(call):
    tid = call.data.split("_")[1]
    msg = bot.send_message(call.message.chat.id, f"Введите новую цену для {tid} мес:")
    bot.register_next_step_handler(msg, lambda m: set_price_proc(m, tid))

def set_price_proc(message, tid):
    try:
        db["settings"]["prices"][tid] = int(message.text)
        save_db(db); bot.send_message(message.chat.id, "✅ Цена обновлена.")
    except: bot.send_message(message.chat.id, "❌ Нужно число.")

def user_manage_proc(message):
    try:
        num = int(message.text)
        uid = next((k for k, v in db["users"].items() if v["number"] == num), None)
        if not uid: return bot.send_message(message.chat.id, "❌ Не найден.")
        u = db["users"][uid]
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("+30 дней", callback_data=f"u_add_{uid}"),
                   types.InlineKeyboardButton("Сбросить срок", callback_data=f"u_zero_{uid}"),
                   types.InlineKeyboardButton("Удалить ключ", callback_data=f"u_delk_{uid}"))
        bot.send_message(message.chat.id, f"Юзер №{num}\nID: {uid}\nСрок: {u['expiry_date']}\nКлюч: {u['token']}", reply_markup=markup)
    except: pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("u_"))
def user_edit_call(call):
    _, act, uid = call.data.split("_")
    u = db["users"][uid]
    if act == "add":
        now = datetime.now()
        start = max(now, datetime.strptime(u["expiry_date"], "%Y-%m-%d %H:%M")) if u["expiry_date"] else now
        u["expiry_date"] = (start + timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
        if not u["token"] and db["vpn_tokens"]: u["token"] = db["vpn_tokens"].pop(0)
    elif act == "zero": u["expiry_date"] = None
    elif act == "delk":
        if u["token"]: db["vpn_tokens"].append(u["token"]); u["token"] = None
    save_db(db); bot.answer_callback_query(call.id, "Готово")

@bot.callback_query_handler(func=lambda c: c.data.startswith("chan_"))
def chan_edit_call(call):
    act = call.data.split("_")[1]
    msg = bot.send_message(call.message.chat.id, "Введите ID канала (напр. -100...):")
    bot.register_next_step_handler(msg, lambda m: chan_proc(m, act))

def chan_proc(message, act):
    try:
        cid = int(message.text)
        if act == "add":
            if cid not in db["channels"]: db["channels"].append(cid)
        else:
            if cid in db["channels"]: db["channels"].remove(cid)
        save_db(db); bot.send_message(message.chat.id, "✅ Каналы обновлены.")
    except: bot.send_message(message.chat.id, "❌ Ошибка ID.")

# ================= ЗАПУСК =================
if __name__ == '__main__':
    threading.Thread(target=expiration_checker, daemon=True).start()
    print("Бот запущен...")
    bot.infinity_polling()

