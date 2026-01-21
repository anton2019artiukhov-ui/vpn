import telebot
import json
import os
import threading
import time
from datetime import datetime, timedelta
from telebot import types

# --- Конфигурация ---
TOKEN = '7967689331:AAFC6El9N8B-zym_uW8jysP4IfelwGznM90'
ADMIN_ID = 2133249292
ADMIN_USERNAME = "@shdjflgldl"
DB_FILE = 'database.json'

bot = telebot.TeleBot(TOKEN)

# --- Работа с базой данных ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "users": {}, 
        "vpn_tokens": [], 
        "settings": {
            "next_user_number": 1,
            "prices": {"1": 300, "3": 855, "6": 1530, "12": 2520}
        }
    }

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

# --- Тексты ---
INSTRUCTION = (
    "📖 **Инструкция по подключению:**\n\n"
    "1. **Установите приложение**: Скачайте **Amnezia VPN** из App Store или Google Play.\n"
    "2. **Скопируйте ключ**: Нажмите на сообщение с ключом выше, чтобы скопировать его.\n"
    "3. **Настройте сервер**: В приложении нажмите «Добавить сервер» или значок «+».\n"
    "4. **Импорт**: Выберите «Настроить вручную» -> «Вставить из буфера обмена».\n"
    "5. **Готово**: Нажмите кнопку подключения. Ваш трафик теперь защищен через Мадрид! 🇪🇸"
)

# --- Клавиатуры ---
def main_kb(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚀 Попробовать (1 день)", "💳 Купить подписку")
    markup.add("👤 Профиль", "📝 Инструкция")
    markup.add("🎁 Реферальная программа", "🆘 Поддержка")
    if int(uid) == ADMIN_ID: markup.add("⚙️ Админ-панель")
    return markup

# --- Фоновая проверка подписок ---
def expiration_checker():
    while True:
        now = datetime.now()
        changed = False
        for uid, u in list(db["users"].items()):
            if not u.get("expiry_date"): continue
            exp = datetime.strptime(u["expiry_date"], "%Y-%m-%d %H:%M")
            
            # Напоминания пользователю
            rem = exp - now
            if timedelta(days=6) < rem <= timedelta(days=7) and not u.get("n7"):
                try: bot.send_message(uid, "🔔 Здравствуйте! Напоминаем, что ваша подписка истекает через 7 дней."); u["n7"] = True; changed = True
                except: pass
            if timedelta(hours=23) < rem <= timedelta(days=1) and not u.get("n1"):
                try: bot.send_message(uid, "🔔 Уважаемый пользователь, до окончания подписки осталось 24 часа. Продлить её можно в меню."); u["n1"] = True; changed = True
                except: pass
            
            # Логика через 24 часа после конца
            if now > exp + timedelta(hours=24) and not u.get("n_admin"):
                if u.get("token"):
                    db["vpn_tokens"].append(u["token"]) # Возврат ключа в пул
                    u["token"] = None
                try: bot.send_message(ADMIN_ID, f"🔴 Подписка пользователя №{u['number']} (ID: {uid}) завершена более 24 часов назад. Ключ возвращен в пул."); u["n_admin"] = True; changed = True
                except: pass
        if changed: save_db(db)
        time.sleep(1200)

# --- Обработчики ---

@bot.message_handler(commands=['start'])
def start(message):
    uid = str(message.from_user.id)
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
            try: bot.send_message(ref, "🎁 Поздравляем! По вашей ссылке зарегистрировался друг. Вам начислено 3 бонусных дня!")
            except: pass
        save_db(db)
    
    bot.send_message(message.chat.id, 
        f"🇪🇸 **Добро пожаловать в Siesta VPN!**\n**.\n"
        "Мы предлагаем премиальный доступ к серверам в Мадриде с высокой скоростью и защитой данных. \n✅Обход белого списка\n ✅Доступ к YouTube, Instagram, Discord и другим без потери скорости интернета\n✅Безлимит ГБ\n✅Высокая скорость", 
        parse_mode="Markdown", reply_markup=main_kb(uid))

@bot.message_handler(func=lambda m: m.text == "🚀 Попробовать (1 день)")
def trial(message):
    uid = str(message.from_user.id)
    u = db["users"][uid]
    if u["trial_used"]: return bot.send_message(message.chat.id, "❌ Вы уже активировали пробный период ранее.")
    if not db["vpn_tokens"]: return bot.send_message(message.chat.id, "😔 К сожалению, сейчас нет свободных ключей. Пожалуйста, попробуйте позже.")
    
    tk = db["vpn_tokens"].pop(0)
    u.update({"trial_used": True, "token": tk, "expiry_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"), "n7": True, "n1": True, "n_admin": False})
    save_db(db)
    bot.send_message(message.chat.id, f"✅ Ваш тестовый доступ на 24 часа активирован!\n\nКлюч:\n`{tk}`", parse_mode="Markdown")
    bot.send_message(message.chat.id, INSTRUCTION, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💳 Купить подписку")
def buy(message):
    uid = str(message.from_user.id)
    d = db["users"][uid].get("discount", 0)
    p = db["settings"]["prices"]
    def get_p(val): return int(val * (1 - d/100))
    
    m_kb = types.InlineKeyboardMarkup()
    m_kb.row(types.InlineKeyboardButton(f"1 мес. — {get_p(p['1'])}₽", callback_data="buy_1"))
    m_kb.row(types.InlineKeyboardButton(f"3 мес. — {get_p(p['3'])}₽ (-5%)", callback_data="buy_3"))
    m_kb.row(types.InlineKeyboardButton(f"6 мес. — {get_p(p['6'])}₽ (-15%)", callback_data="buy_6"))
    m_kb.row(types.InlineKeyboardButton(f"1 год — {get_p(p['12'])}₽ (-30%)", callback_data="buy_12"))
    
    text = "💳 **Выберите срок подписки:**\n\nПри покупке любой подписки вы получите дополнительные **2 дня** в подарок!"
    if d > 0: text += f"\n\n🔥 У вас действует персональная скидка: **{d}%**"
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=m_kb)

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
    bot.send_message(call.message.chat.id, f"✅ Спасибо! Подписка продлена на {days} дн. до **{u['expiry_date']}**\n\nВаш ключ:\n`{u['token']}`", parse_mode="Markdown")
    bot.send_message(call.message.chat.id, INSTRUCTION, parse_mode="Markdown")

# --- Админ-панель ---
@bot.message_handler(func=lambda m: m.text == "⚙️ Админ-панель" and m.from_user.id == ADMIN_ID)
def admin_menu(message):
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton("➕ Добавить ключи", callback_data="adm_add"),
          types.InlineKeyboardButton("🔑 Статус ключей", callback_data="adm_keys"))
    m.add(types.InlineKeyboardButton("💰 Цены", callback_data="adm_prices"),
          types.InlineKeyboardButton("📊 Статистика", callback_data="adm_stats"))
    m.add(types.InlineKeyboardButton("📢 Рассылка", callback_data="adm_mail"),
          types.InlineKeyboardButton("👤 Юзер-менеджер", callback_data="adm_user"))
    bot.send_message(message.chat.id, "🛠 Меню администратора:", reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_"))
def admin_actions(call):
    if call.data == "adm_add":
        msg = bot.send_message(call.message.chat.id, "Введите ключ (или список через Enter):")
        bot.register_next_step_handler(msg, save_keys)
    elif call.data == "adm_stats":
        total = len(db["users"])
        active = sum(1 for u in db["users"].values() if u["expiry_date"] and datetime.strptime(u["expiry_date"], "%Y-%m-%d %H:%M") > datetime.now())
        bot.send_message(call.message.chat.id, f"📊 Статистика:\n- Всего юзеров: {total}\n- Активных подписок: {active}\n- Ключей в запасе: {len(db['vpn_tokens'])}")
    elif call.data == "adm_prices":
        m = types.InlineKeyboardMarkup()
        for k, v in db["settings"]["prices"].items():
            m.add(types.InlineKeyboardButton(f"{k} мес -> {v}₽", callback_data=f"setpr_{k}"))
        bot.send_message(call.message.chat.id, "Выберите тариф для изменения цены:", reply_markup=m)
    elif call.data == "adm_mail":
        msg = bot.send_message(call.message.chat.id, "Введите текст для общей рассылки:")
        bot.register_next_step_handler(msg, broadcast)
    elif call.data == "adm_user":
        msg = bot.send_message(call.message.chat.id, "Введите порядковый номер пользователя (№):")
        bot.register_next_step_handler(msg, user_manage)
    elif call.data == "adm_keys":
        text = "🔑 **Статус по ключам:**\n\n**Занятые ключи:**\n"
        found = False
        for uid, u in db["users"].items():
            if u["token"]:
                text += f"№{u['number']} (ID {uid}) — до {u['expiry_date']}\n`{u['token']}`\n\n"
                found = True
        if not found: text += "Нет занятых ключей.\n"
        text += f"\n**В пуле (свободно):** {len(db['vpn_tokens'])} шт."
        m = types.InlineKeyboardMarkup()
        m.add(types.InlineKeyboardButton("🗑 Очистить свободные ключи", callback_data="adm_clear_pool"))
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data == "adm_clear_pool")
def clear_pool(call):
    db["vpn_tokens"] = []
    save_db(db)
    bot.answer_callback_query(call.id, "Пул очищен")

def save_keys(message):
    new_keys = message.text.split('\n')
    db["vpn_tokens"].extend([k.strip() for k in new_keys if k.strip()])
    save_db(db)
    bot.send_message(message.chat.id, f"✅ Добавлено ключей: {len(new_keys)}")

def broadcast(message):
    count = 0
    for uid in db["users"]:
        try: bot.send_message(uid, message.text); count += 1
        except: pass
    bot.send_message(message.chat.id, f"✅ Рассылка завершена. Доставлено: {count}")

@bot.callback_query_handler(func=lambda c: c.data.startswith("setpr_"))
def set_pr_val(call):
    t_id = call.data.split("_")[1]
    msg = bot.send_message(call.message.chat.id, f"Введите новую цену для тарифа {t_id} мес:")
    bot.register_next_step_handler(msg, lambda m: finish_price(m, t_id))

def finish_price(message, t_id):
    try:
        db["settings"]["prices"][t_id] = int(message.text)
        save_db(db)
        bot.send_message(message.chat.id, "✅ Цена успешно изменена.")
    except: bot.send_message(message.chat.id, "❌ Ошибка: введите число.")

def user_manage(message):
    try:
        num = int(message.text)
        uid = next((k for k, v in db["users"].items() if v["number"] == num), None)
        if not uid: return bot.send_message(message.chat.id, "❌ Пользователь не найден.")
        u = db["users"][uid]
        m = types.InlineKeyboardMarkup()
        m.add(types.InlineKeyboardButton("+30 дней", callback_data=f"edit_add_{uid}"),
              types.InlineKeyboardButton("Обнулить срок", callback_data=f"edit_zero_{uid}"))
        m.add(types.InlineKeyboardButton("Дать скидку 50%", callback_data=f"edit_disc_{uid}"),
              types.InlineKeyboardButton("Удалить ключ", callback_data=f"edit_delk_{uid}"))
        txt = f"👤 Юзер №{num}\nID: `{uid}`\nДо: {u['expiry_date'] or 'Нет'}\nСкидка: {u['discount']}%\nКлюч: `{u['token'] or 'Нет'}`"
        bot.send_message(message.chat.id, txt, parse_mode="Markdown", reply_markup=m)
    except: bot.send_message(message.chat.id, "❌ Неверный формат.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_"))
def edit_user_callback(call):
    _, act, uid = call.data.split("_")
    u = db["users"][uid]
    if act == "add":
        now = datetime.now()
        start_dt = max(now, datetime.strptime(u["expiry_date"], "%Y-%m-%d %H:%M")) if u["expiry_date"] else now
        u["expiry_date"] = (start_dt + timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
        if not u["token"] and db["vpn_tokens"]: u["token"] = db["vpn_tokens"].pop(0)
    elif act == "zero": u["expiry_date"] = None
    elif act == "disc": u["discount"] = 50
    elif act == "delk":
        if u["token"]: db["vpn_tokens"].append(u["token"]); u["token"] = None
    save_db(db)
    bot.answer_callback_query(call.id, "Выполнено")

# --- Общие кнопки ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(message):
    uid = str(message.from_user.id)
    u = db["users"][uid]
    m = types.InlineKeyboardMarkup()
    if u["balance_days"] > 0: m.add(types.InlineKeyboardButton("🎁 Активировать бонусы", callback_data="claim"))
    exp = u["expiry_date"] if u["expiry_date"] else "Подписка не активна"
    bot.send_message(message.chat.id, 
        f"👤 **Ваш профиль №{u['number']}**\n\n📅 Срок до: **{exp}**\n🎁 Бонусные дни: **{u['balance_days']}**\n"
        f"🔑 Ваш ключ: `{u['token'] or 'Не получен'}`", 
        parse_mode="Markdown", reply_markup=m)

@bot.callback_query_handler(func=lambda c: c.data == "claim")
def claim_bonus(call):
    uid = str(call.from_user.id)
    u = db["users"][uid]
    if u["balance_days"] > 0:
        now = datetime.now()
        start = max(now, datetime.strptime(u["expiry_date"], "%Y-%m-%d %H:%M")) if u["expiry_date"] else now
        u["expiry_date"] = (start + timedelta(days=u["balance_days"])).strftime("%Y-%m-%d %H:%M")
        b = u["balance_days"]
        u["balance_days"] = 0
        save_db(db)
        bot.send_message(call.message.chat.id, f"✅ Бонусные дни ({b} дн.) успешно добавлены к вашей подписке! Новый срок: **{u['expiry_date']}**", parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Зачислено")

@bot.message_handler(func=lambda m: m.text == "🎁 Реферальная программа")
def referral(message):
    link = f"https://t.me/{bot.get_me().username}?start={message.from_user.id}"
    bot.send_message(message.chat.id, 
        f"🎁 **Приглашайте друзей и пользуйтесь VPN бесплатно!**\n\n"
        f"За каждого друга, который перейдет по вашей ссылке, вы получите **3 дня** подписки в подарок.\n\n"
        f"Ваша ссылка:\n{link}", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🆘 Поддержка")
def support(message):
    bot.send_message(message.chat.id, f"🆘 По всем вопросам и для оплаты обращайтесь к администратору: {ADMIN_USERNAME}")

@bot.message_handler(func=lambda m: m.text == "📝 Инструкция")
def show_instruction(message):
    bot.send_message(message.chat.id, INSTRUCTION, parse_mode="Markdown")

if __name__ == '__main__':
    threading.Thread(target=expiration_checker, daemon=True).start()
    bot.infinity_polling()
