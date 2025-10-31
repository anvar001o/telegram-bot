import telebot
from telebot import types
import json
import requests

# ===== TOKEN va ADMIN ID =====
TOKEN = "8326085441:AAE8Tit1xqU1kJsvDnAHJIz5ysFFf9AO_6Q"
ADMIN_ID = 5101290485

# ===== SMMYA API =====
API_KEY = "0e29603dd8c04147c042806c175052e9"
API_URL = "https://smmya.com/api/v2"

bot = telebot.TeleBot(TOKEN)
orders = {}


# ===== Buyurtmalarni saqlash =====
def save_orders():
    with open("orders.json", "w", encoding="utf-8") as f:
        json.dump(orders, f, ensure_ascii=False, indent=4)


# ===== APIga buyurtma yuborish =====
def send_order_to_smmya(service_id, quantity, username):
    data = {
        "key": API_KEY,
        "action": "add",
        "service": service_id,
        "quantity": quantity,
        "link": username
    }
    response = requests.post(API_URL, data=data)
    try:
        return response.json()
    except:
        return {"error": "API bilan bog‘lanishda xato."}


# ===== Username so‘rash =====
def ask_username_step(message):
    msg = "➡️ Qaysi username uchun olmoqchisiz? (masalan: @nickname)\n\nYoki pastdagi tugmadan '⭐ O‘zim uchun'ni bosing 👇"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⭐ O‘zim uchun", callback_data="self_user"))
    bot.send_message(message.chat.id, msg, reply_markup=markup)
    bot.register_next_step_handler(message, process_username)


def process_username(message):
    user_id = str(message.from_user.id)
    username = message.text.strip()

    # Username tekshirish
    if not username.startswith("@"):
        bot.send_message(message.chat.id, "❌ Username '@' bilan boshlanishi kerak.")
        bot.register_next_step_handler(message, process_username)
        return

    # Username mavjudligini tekshirish
    check = requests.get(f"https://t.me/{username[1:]}")
    if check.status_code != 200:
        bot.send_message(message.chat.id, "❌ Bunday username mavjud emas. Qayta kiriting.")
        bot.register_next_step_handler(message, process_username)
        return

    orders[user_id]["username"] = username
    save_orders()
    confirm_order(message.chat.id, user_id)


# ===== Callback: O‘zim uchun =====
@bot.callback_query_handler(func=lambda call: call.data == "self_user")
def self_user_selected(call):
    user_id = str(call.from_user.id)
    username = f"@{call.from_user.username}" if call.from_user.username else f"user_{user_id}"
    orders[user_id]["username"] = username
    save_orders()
    bot.answer_callback_query(call.id, "👤 Sizning username belgilandi!")
    confirm_order(call.message.chat.id, user_id)


# ===== Stars miqdorini olish =====
def process_amount(message):
    user_id = str(message.from_user.id)
    try:
        amount = int(message.text.strip())
        if amount < 50:
            bot.send_message(message.chat.id, "❌ Minimal 50 ta stars!")
            bot.register_next_step_handler(message, process_amount)
            return
        orders[user_id]["amount"] = amount
        orders[user_id]["price"] = amount * 210
        save_orders()
        ask_username_step(message)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Faqat raqam kiriting!")
        bot.register_next_step_handler(message, process_amount)


# ===== Premium variantlari =====
def ask_premium_plan(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💎 1 oylik – 40 000 so‘m", callback_data="premium_1m"),
        types.InlineKeyboardButton("💎 3 oylik – 150 000 so‘m", callback_data="premium_3m"),
        types.InlineKeyboardButton("💎 6 oylik – 209 000 so‘m", callback_data="premium_6m"),
        types.InlineKeyboardButton("💎 12 oylik – 384 000 so‘m", callback_data="premium_12m")
    )
    bot.send_message(message.chat.id, "💎 Premium turini tanlang:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("premium_"))
def premium_selected(call):
    user_id = str(call.from_user.id)
    plans = {
        "premium_1m": (1, 90000, 471),
        "premium_3m": (3, 156000, 468),
        "premium_6m": (6, 208000, 469),
        "premium_12m": (12, 384000, 470)
    }
    months, price, service_id = plans[call.data]
    orders[user_id]["amount"] = f"{months} oy"
    orders[user_id]["price"] = price
    orders[user_id]["service_id"] = service_id
    save_orders()
    bot.answer_callback_query(call.id)

    # 1 oylik bo‘lsa — admin lichkasiga yuborish
    if months == 1:
        bot.send_message(call.message.chat.id, "👉 1 oylik premium xaridi uchun @anvar001o bilan bog‘laning.")
    else:
        ask_username_step(call.message)


# ===== Buyurtmani tasdiqlash =====
def confirm_order(chat_id, user_id):
    order = orders[user_id]
    product = "⭐️ Stars" if order["product"] == "stars" else "💎 Premium"
    price = f"{order['price']:,}"

    msg = (
        f"✅ Buyurtma ma'lumotlari:\n\n"
        f"{product}\n"
        f"💰 Jami: {price} so‘m\n"
        f"👤 Username: {order['username']}\n\n"
        f"💳 To‘lov uchun karta:\n<code>4067 0700 0847 0457</code>\n\n"
        f"To‘lovni amalga oshirgach, ✅ 'To‘lov qildim'ni bosing."
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 Karta raqamini nusxalash", callback_data="copy_card"))
    markup.add(types.InlineKeyboardButton("✅ To‘lov qildim", callback_data="paid_confirm"))

    bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=markup)


# ===== Callback: Karta nusxalash =====
@bot.callback_query_handler(func=lambda call: call.data == "copy_card")
def copy_card_number(call):
    bot.answer_callback_query(call.id, text="💳 Karta raqami nusxalandi!")
    bot.send_message(call.message.chat.id, "💳 Nusxalash uchun karta raqami:\n<code>4067 0700 0847 0457</code>",
                     parse_mode="HTML")


# ===== /start =====
@bot.message_handler(commands=["start"])
def start(message):
    user_id = str(message.from_user.id)

    # 🔹 Eski step handlerlarni tozalaymiz
    bot.clear_step_handler_by_chat_id(chat_id=message.chat.id)

    # 🔹 Yangi session ochamiz
    orders[user_id] = {"product": None, "amount": 0, "price": 0, "username": "", "chat_id": message.chat.id}
    save_orders()

    # 🔹 Pastdagi reply keyboardni yopamiz
    remove = types.ReplyKeyboardRemove()

    # 🔹 Inline menyu chiqaramiz
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("⭐️ Stars", callback_data="choose_stars"),
        types.InlineKeyboardButton("💎 Premium", callback_data="choose_premium")
    )

    bot.send_message(
        message.chat.id,
        "👋 Salom! Quyidagilardan birini tanlang:",
        reply_markup=markup
    )


# ===== Mahsulot tanlash =====
@bot.callback_query_handler(func=lambda call: call.data in ["choose_stars", "choose_premium"])
def choose_product(call):
    user_id = str(call.from_user.id)
    if call.data == "choose_stars":
        orders[user_id]["product"] = "stars"
        save_orders()
        bot.send_message(call.message.chat.id, "⭐️ Nechta stars olmoqchisiz? (minimal 50)")
        bot.register_next_step_handler(call.message, process_amount)
    else:
        orders[user_id]["product"] = "premium"
        save_orders()
        ask_premium_plan(call.message)


# ===== Foydalanuvchi to‘lov qildi =====
@bot.callback_query_handler(func=lambda call: call.data == "paid_confirm")
def paid_confirm(call):
    user_id = str(call.from_user.id)
    order = orders[user_id]
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "✅ To‘lov tekshiruvida! Admin tasdiqlashini kuting.")

    admin_msg = (
        f"📥 Yangi to‘lov!\n"
        f"👤 Foydalanuvchi: @{call.from_user.username}\n"
        f"Mahsulot: {'⭐️ Stars' if order['product'] == 'stars' else '💎 Premium'}\n"
        f"Miqdor: {order['amount']}\n"
        f"Narx: {order['price']} so‘m\n"
        f"Username: {order['username']}\n\n"
        f"✅ yoki ❌ bilan javob bering."
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"admin_ok_{user_id}"),
        types.InlineKeyboardButton("❌ Rad etish", callback_data=f"admin_no_{user_id}")
    )
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)


# ===== Admin qarori =====
@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_action(call):
    parts = call.data.split("_")
    if len(parts) < 3:
        return
    _, action, user_id = parts
    order = orders[user_id]

    if action == "ok":
        if order["product"] == "stars":
            res = send_order_to_smmya(467, order["amount"], order["username"])
        else:
            res = send_order_to_smmya(order["service_id"], 1, order["username"])

        if "order" in res:
            bot.send_message(order["chat_id"], "✅ To‘lov tasdiqlandi! Xaridingiz 1 daqiqa ichida tushadi.")
            bot.edit_message_text("✅ Buyurtma tasdiqlandi va API yuborildi!", call.message.chat.id,
                                  call.message.message_id)
        else:
            bot.send_message(order["chat_id"], f"⚠️ Xatolik: {res}")
            bot.edit_message_text("⚠️ API bilan muammo!", call.message.chat.id, call.message.message_id)
    elif action == "no":
        bot.send_message(order["chat_id"], "❌ To‘lov rad etildi. Iltimos, to‘lovni qayta urinib ko‘ring.")
        bot.edit_message_text("❌ Buyurtma rad etildi.", call.message.chat.id, call.message.message_id)


# ===== RUN =====
print("🤖 Bot ishga tushdi...")
bot.polling(none_stop=True)
