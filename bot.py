import os
import logging

from telegram import Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest

from config import TELEGRAM_BOT_TOKEN, PSD_TEMPLATE_PATH, OUTPUT_DIR, USER_IMAGE_DIR

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎉 እንኳን ደህና መጡ!\n📸 ፎቶዎን ይላኩ።"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send a photo and I will compose it onto our PSD template!\n"
        "The bot will automatically remove the background and fit your face to the frame."
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    processing_msg = await update.message.reply_text(
        "⏳ ፎቶው በተጠናቀቀ ስራ ላይ ነው... ትንሽ ይጠብቁ"
    )

    user_id = update.effective_user.id
    os.makedirs(USER_IMAGE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    input_path = f"{USER_IMAGE_DIR}/{user_id}.jpg"
    output_path = f"{OUTPUT_DIR}/{user_id}_out.jpg"

    try:
        if not update.message.photo:
            await update.message.reply_text("❗ እባክዎን ፎቶ ብቻ ይላኩ።")
            return

        photo = await update.message.photo[-1].get_file()
        if photo.file_size > 8 * 1024 * 1024:
            await update.message.reply_text("❌ ፎቶዎ ከ8MB በላይ ነው። እባክዎ ያነሰ ፎቶ ይላኩ።")
            return

        await photo.download_to_drive(input_path)

        from image_processor import process_image_with_psd

        try:
            process_image_with_psd(input_path, PSD_TEMPLATE_PATH, output_path)
        except FileNotFoundError as e:
            await update.message.reply_text("🔴 Template PSD አልተገኘም። መንገድ፡ psd_templates/template.psd")
            logger.error(e)
            return
        except ValueError as e:
            await update.message.reply_text("📛 ፎቶዎ ዳግም ይሞክሩ፤ አንዳንድ ፎቶዎች የተበላሸ ናቸው።")
            logger.error(e)
            return
        except Exception as e:
            logger.error(f"Unknown error: {str(e)}")
            await update.message.reply_text("❌ ድጋሚ ይሞክሩ፣ ችግር ተፈጥሯል።")
            return

        with open(output_path, "rb") as f:
            await update.message.reply_photo(
                photo=InputFile(f),
                caption="✅ በተሳካ ሁኔታ አልቋል!"
            )
    except Exception as e:
        logger.error(f"Top-level handler error: {e}")
        await update.message.reply_text("🔴 ይህን ፎቶ ማቅረብ አልተቻለም። ደግመው ይሞክሩ።")
    finally:
        for p in [input_path, output_path]:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception as clean_e:
                logger.warning(f"Cleanup failed: {clean_e}")

        try:
            await processing_msg.delete()
        except Exception as del_e:
            logger.debug(f"Could not delete processing message: {del_e}")

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Missing token - set TELEGRAM_BOT_TOKEN in your environment or .env file.")
        return

    request = HTTPXRequest(connect_timeout=30, read_timeout=30)
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).request(request).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()