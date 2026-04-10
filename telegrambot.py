# ═══════════════════════════════════════════════════════════
# 🤖 بوت تيليغرام لتنزيل الفيديوهات
# يدعم: YouTube | Instagram | TikTok
# مُحسَّن للتشغيل على Google Colab
# ═══════════════════════════════════════════════════════════
#
# 📦 السيل الأول — تثبيت المكتبات (شغّله مرة وحدة):
#   !pip install python-telegram-bot yt-dlp nest_asyncio flask
#
# ⚙️  السيل الثاني — غيّر التوكن فقط ثم شغّل الكود
# ═══════════════════════════════════════════════════════════

import os
import logging
import asyncio
import threading
import nest_asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import yt_dlp

nest_asyncio.apply()

# ───────────────────────────────────────────────────────────
# ⚙️  الإعدادات — غيّر التوكن هنا فقط
# ───────────────────────────────────────────────────────────
BOT_TOKEN        = "8390939059:AAEJ5jeIE465IfHBlxMhPwSQn4xpOFNSHjM"   # ← غيّر هذا فقط
DOWNLOAD_DIR     = "downloads"
COOKIES_FILE     = "www.instagram.com_cookies.txt"          # ارفع الملف على Colab بنفس الاسم
REQUIRED_CHANNEL = "@ixm_iii"            # ← القناة الإجبارية

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# ───────────────────────────────────────────────────────────
# 🌐 Flask Server — يمنع Colab من الإيقاف التلقائي
# ───────────────────────────────────────────────────────────
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "✅ البوت شغال!"

threading.Thread(
    target=lambda: flask_app.run(host="0.0.0.0", port=8080),
    daemon=True
).start()


# ───────────────────────────────────────────────────────────
# ✅ التحقق من الاشتراك بالقناة
# ───────────────────────────────────────────────────────────
async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    if await is_subscribed(user_id, context):
        return True

    keyboard = [[
        InlineKeyboardButton("📢 اشترك بالقناة", url=f"https://t.me/{REQUIRED_CHANNEL.lstrip('@')}"),
        InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub"),
    ]]
    await update.effective_message.reply_text(
        "⚠️ لازم تشترك بالقناة أول!\n\n"
        f"📢 القناة: {REQUIRED_CHANNEL}\n\n"
        "بعد الاشتراك اضغط ✅ تحقق من الاشتراك",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return False


# ───────────────────────────────────────────────────────────
# 🔍 تحديد المنصة من الرابط
# ───────────────────────────────────────────────────────────
def detect_platform(url: str) -> str:
    url = url.lower()
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    elif "instagram.com" in url:
        return "instagram"
    elif "tiktok.com" in url:
        return "tiktok"
    return "unknown"


# ───────────────────────────────────────────────────────────
# ⬇️  دالة التنزيل — مع فورمات خاص لكل منصة
# ───────────────────────────────────────────────────────────
def download_video(url: str, quality: str = "best", platform: str = "youtube") -> tuple:

    if platform in ("instagram", "tiktok"):
        format_map = {
            "best":   "best[ext=mp4]/best",
            "medium": "best[height<=480][ext=mp4]/best[height<=480]/best",
            "audio":  "bestaudio/best",
        }
    else:
        format_map = {
            "best":   "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "medium": "bestvideo[height<=480][ext=mp4]+bestaudio/best[height<=480]",
            "audio":  "bestaudio[ext=m4a]/bestaudio",
        }

    ydl_opts = {
        "format":               format_map.get(quality, "best"),
        "outtmpl":              f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "quiet":                True,
        "no_warnings":          True,
        "merge_output_format":  "mp4",
    }

    if os.path.exists(COOKIES_FILE):
        ydl_opts["cookiefile"] = COOKIES_FILE
        logger.info("✅ الكوكيز محملة")
    else:
        logger.warning("⚠️ cookies.txt مو موجود — Instagram قد يفشل")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info     = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if not os.path.exists(filename):
                filename = filename.rsplit(".", 1)[0] + ".mp4"
            return True, filename
    except Exception as e:
        logger.error(f"خطأ: {e}")
        return False, str(e)


# ───────────────────────────────────────────────────────────
# 📩 /start
# ───────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_subscription(update, context):
        return
    await update.message.reply_text(
        "👋 أهلاً! أنا بوت تنزيل الفيديوهات 🎬\n\n"
        "📌 المنصات المدعومة:\n"
        "  ▶️  YouTube\n"
        "  📸  Instagram\n"
        "  🎵  TikTok\n\n"
        "أرسل لي الرابط مباشرة وأنا أتولى الباقي! 🚀"
    )


# ───────────────────────────────────────────────────────────
# 📩 /help
# ───────────────────────────────────────────────────────────
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_subscription(update, context):
        return
    await update.message.reply_text(
        "📖 طريقة الاستخدام:\n\n"
        "1️⃣ أرسل رابط الفيديو\n"
        "2️⃣ اختار الجودة\n"
        "3️⃣ انتظر وستصلك الفيديو ✅\n\n"
        "الأوامر:\n"
        "/start — بدء البوت\n"
        "/help  — المساعدة"
    )


# ───────────────────────────────────────────────────────────
# 🔗 استقبال الروابط وعرض أزرار الجودة
# ───────────────────────────────────────────────────────────
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_subscription(update, context):
        return

    url      = update.message.text.strip()
    platform = detect_platform(url)

    if platform == "unknown":
        await update.message.reply_text(
            "❌ الرابط غير مدعوم!\n"
            "أرسل رابط من YouTube أو Instagram أو TikTok."
        )
        return

    icons = {"youtube": "▶️", "instagram": "📸", "tiktok": "🎵"}
    context.user_data["url"]      = url
    context.user_data["platform"] = platform

    keyboard = [
        [
            InlineKeyboardButton("🏆 أفضل جودة",    callback_data="q_best"),
            InlineKeyboardButton("📱 جودة متوسطة", callback_data="q_medium"),
        ],
        [
            InlineKeyboardButton("🎵 صوت فقط",      callback_data="q_audio"),
        ],
    ]
    await update.message.reply_text(
        f"{icons[platform]} تم اكتشاف رابط *{platform.capitalize()}*\n\nاختار الجودة:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# ───────────────────────────────────────────────────────────
# 🔄 زر التحقق من الاشتراك
# ───────────────────────────────────────────────────────────
async def handle_check_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if await is_subscribed(user_id, context):
        await query.edit_message_text(
            "✅ تم التحقق! أنت مشترك.\n\n"
            "هسه أرسل لي رابط الفيديو وأنا أنزله لك 🚀"
        )
    else:
        keyboard = [[
            InlineKeyboardButton("📢 اشترك بالقناة", url=f"https://t.me/{REQUIRED_CHANNEL.lstrip('@')}"),
            InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub"),
        ]]
        await query.edit_message_text(
            "❌ ما اشتركت بعد!\n\n"
            f"اشترك بـ {REQUIRED_CHANNEL} ثم اضغط تحقق مجدداً.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


# ───────────────────────────────────────────────────────────
# 🎛️  معالجة اختيار الجودة والتنزيل
# ───────────────────────────────────────────────────────────
async def handle_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await query.answer()

    quality = query.data.replace("q_", "")
    url     = context.user_data.get("url")

    if not url:
        await query.edit_message_text("⚠️ انتهت الجلسة، أرسل الرابط مجدداً.")
        return

    platform = context.user_data.get("platform", "youtube")
    labels   = {"best": "أفضل جودة 🏆", "medium": "جودة متوسطة 📱", "audio": "صوت فقط 🎵"}
    await query.edit_message_text(f"⏳ جاري التنزيل — {labels[quality]}\nانتظر قليلاً...")

    success, result = download_video(url, quality, platform)

    if not success:
        await query.message.reply_text(f"❌ فشل التنزيل!\n\n`{result}`", parse_mode="Markdown")
        return

    try:
        size_mb = os.path.getsize(result) / (1024 * 1024)
        if size_mb > 50:
            await query.message.reply_text(
                f"⚠️ حجم الملف كبير ({size_mb:.1f} MB)\n"
                "تيليغرام يقبل أقل من 50MB.\n"
                "جرّب الجودة المتوسطة أو الصوت فقط."
            )
        elif quality == "audio":
            await query.message.reply_audio(
                audio=open(result, "rb"),
                caption="✅ تم التنزيل بنجاح! 🎉"
            )
        else:
            await query.message.reply_video(
                video=open(result, "rb"),
                caption="✅ تم التنزيل بنجاح! 🎉"
            )
    except Exception as e:
        await query.message.reply_text(f"❌ خطأ في الإرسال: {e}")
    finally:
        if os.path.exists(result):
            os.remove(result)
        context.user_data.pop("url", None)


# ───────────────────────────────────────────────────────────
# 🚀 تشغيل البوت
# ───────────────────────────────────────────────────────────
async def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help",  help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(handle_check_sub, pattern="^check_sub$"))
    app.add_handler(CallbackQueryHandler(handle_quality,   pattern="^q_"))

    logger.info("✅ البوت شغال!")
    await app.run_polling()

asyncio.get_event_loop().run_until_complete(run_bot())
