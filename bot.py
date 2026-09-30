import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

TOKEN = os.getenv("BOT_TOKEN", "PASTE_BOT_TOKEN_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
DB = "shop.db"

def db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        description TEXT DEFAULT ''
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        status TEXT DEFAULT 'pending'
    )""")
    con.commit()
    return con

def seed():
    con = db()
    if con.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        con.execute(
            "INSERT INTO products(name,price,description) VALUES(?,?,?)",
            ("نمونه پک", 500000, "توضیحات محصول")
        )
        con.execute(
            "INSERT INTO products(name,price,description) VALUES(?,?,?)",
            ("آپدیت پک", 400000, "توضیحات محصول")
        )
        con.commit()
    con.close()

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍 خرید پک", callback_data="products"),
         InlineKeyboardButton("📦 لیست محصولات", callback_data="products")],
        [InlineKeyboardButton("🧾 سفارش‌های من", callback_data="orders"),
         InlineKeyboardButton("🎧 پشتیبانی", callback_data="support")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"سلام {update.effective_user.first_name} ❤️\n\n"
        "به فروشگاه خوش آمدید.\n"
        "از منوی زیر محصول موردنظر را انتخاب کنید."
    )
    await update.message.reply_text(text, reply_markup=main_menu())

async def products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    con = db()
    rows = con.execute("SELECT id,name,price,description FROM products").fetchall()
    con.close()

    buttons = []
    for pid, name, price, desc in rows:
        buttons.append([InlineKeyboardButton(
            f"{name} — {price:,} تومان",
            callback_data=f"product:{pid}"
        )])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="home")])
    await q.edit_message_text("🛍 لیست محصولات:", reply_markup=InlineKeyboardMarkup(buttons))

async def product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    pid = int(q.data.split(":")[1])
    con = db()
    row = con.execute(
        "SELECT name,price,description FROM products WHERE id=?", (pid,)
    ).fetchone()
    con.close()
    if not row:
        await q.edit_message_text("محصول پیدا نشد.")
        return

    name, price, desc = row
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 ثبت سفارش", callback_data=f"buy:{pid}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="products")]
    ])
    await q.edit_message_text(
        f"📦 {name}\n\n{desc}\n\n💰 قیمت: {price:,} تومان",
        reply_markup=kb
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    pid = int(q.data.split(":")[1])

    con = db()
    con.execute(
        "INSERT INTO orders(user_id,product_id) VALUES(?,?)",
        (q.from_user.id, pid)
    )
    con.commit()
    order_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    row = con.execute("SELECT name,price FROM products WHERE id=?", (pid,)).fetchone()
    con.close()

    name, price = row
    await q.edit_message_text(
        f"✅ سفارش #{order_id} ثبت شد.\n\n"
        f"📦 محصول: {name}\n"
        f"💰 مبلغ: {price:,} تومان\n\n"
        "برای تکمیل پرداخت با پشتیبانی تماس بگیرید.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎧 پشتیبانی", callback_data="support")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="home")]
        ])
    )

async def orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    con = db()
    rows = con.execute("""
        SELECT o.id,p.name,p.price,o.status
        FROM orders o JOIN products p ON p.id=o.product_id
        WHERE o.user_id=? ORDER BY o.id DESC
    """, (q.from_user.id,)).fetchall()
    con.close()

    if not rows:
        text = "🧾 هنوز سفارشی ثبت نکرده‌اید."
    else:
        text = "🧾 سفارش‌های شما:\n\n" + "\n".join(
            f"#{oid} — {name} — {price:,} تومان — {status}"
            for oid,name,price,status in rows
        )
    await q.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]
        ])
    )

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🎧 پشتیبانی\n\nبرای پشتیبانی، پیام خود را ارسال کنید.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]
        ])
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "ℹ️ راهنما\n\n"
        "1. محصول را انتخاب کنید.\n"
        "2. ثبت سفارش را بزنید.\n"
        "3. مراحل پرداخت را از پشتیبانی دریافت کنید.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]
        ])
    )

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.data == "home":
        await q.answer()
        await q.edit_message_text("🏠 منوی اصلی", reply_markup=main_menu())
    elif q.data == "products":
        await products(update, context)
    elif q.data.startswith("product:"):
        await product_detail(update, context)
    elif q.data.startswith("buy:"):
        await buy(update, context)
    elif q.data == "orders":
        await orders(update, context)
    elif q.data == "support":
        await support(update, context)
    elif q.data == "help":
        await help_cmd(update, context)

if __name__ == "__main__":
    if TOKEN == "PASTE_BOT_TOKEN_HERE":
        raise SystemExit("BOT_TOKEN را تنظیم کنید.")
    seed()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    print("Bot is running...")
    app.run_polling()
